from __future__ import annotations

import sqlite3
from pathlib import Path

from mindsetbench.models.prompt import Condition
from mindsetbench.models.run import TrialRecord
from mindsetbench.runner.config import ExperimentConfig


class ResultStore:
    """SQLite-backed, idempotent trial store suitable for resumable runs."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._create_schema()

    def _create_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS experiments (
                experiment_id TEXT PRIMARY KEY,
                config_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS trials (
                experiment_id TEXT NOT NULL,
                model TEXT NOT NULL,
                case_id TEXT NOT NULL,
                condition TEXT NOT NULL,
                sample_index INTEGER NOT NULL,
                prompt_sha256 TEXT NOT NULL,
                correct INTEGER NOT NULL,
                matched_copy_probe INTEGER NOT NULL,
                record_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (experiment_id, model, case_id, condition, sample_index),
                FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
            );
            CREATE INDEX IF NOT EXISTS idx_trials_experiment ON trials(experiment_id);
            CREATE INDEX IF NOT EXISTS idx_trials_case ON trials(case_id);
            """
        )
        self._connection.commit()

    def register_experiment(self, config: ExperimentConfig) -> None:
        serialized = config.model_dump_json()
        existing = self._connection.execute(
            "SELECT config_json FROM experiments WHERE experiment_id = ?",
            (config.experiment_id,),
        ).fetchone()
        if existing is not None:
            try:
                existing_config = ExperimentConfig.model_validate_json(existing[0])
            except ValueError as exc:
                raise ValueError(
                    f"experiment {config.experiment_id!r} has an invalid stored config"
                ) from exc
            if existing_config != config:
                raise ValueError(
                    f"experiment {config.experiment_id!r} already exists with a different config"
                )
        self._connection.execute(
            "INSERT OR IGNORE INTO experiments(experiment_id, config_json) VALUES (?, ?)",
            (config.experiment_id, serialized),
        )
        self._connection.commit()

    def has_trial(
        self,
        experiment_id: str,
        model: str,
        case_id: str,
        condition: Condition,
        sample_index: int,
    ) -> bool:
        row = self._connection.execute(
            """
            SELECT 1 FROM trials
            WHERE experiment_id=? AND model=? AND case_id=? AND condition=? AND sample_index=?
            """,
            (experiment_id, model, case_id, condition.value, sample_index),
        ).fetchone()
        return row is not None

    def save_trial(self, record: TrialRecord) -> bool:
        cursor = self._connection.execute(
            """
            INSERT OR IGNORE INTO trials(
                experiment_id, model, case_id, condition, sample_index,
                prompt_sha256, correct, matched_copy_probe, record_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.experiment_id,
                record.model,
                record.case_id,
                record.condition.value,
                record.sample_index,
                record.prompt.prompt_sha256,
                int(record.grade.correct),
                int(record.grade.matched_copy_probe),
                record.model_dump_json(),
                record.created_at.isoformat(),
            ),
        )
        self._connection.commit()
        return cursor.rowcount == 1

    def load_trials(self, experiment_id: str) -> list[TrialRecord]:
        rows = self._connection.execute(
            """
            SELECT record_json FROM trials
            WHERE experiment_id=?
            ORDER BY case_id, condition, sample_index
            """,
            (experiment_id,),
        ).fetchall()
        return [TrialRecord.model_validate_json(row[0]) for row in rows]

    def trial_count(self, experiment_id: str) -> int:
        row = self._connection.execute(
            "SELECT COUNT(*) FROM trials WHERE experiment_id=?", (experiment_id,)
        ).fetchone()
        return int(row[0]) if row else 0

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> ResultStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
