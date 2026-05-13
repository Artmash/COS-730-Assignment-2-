import sqlite3
import os

DB_NAME = "submission_review.db"

def setup_database():
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE submissions (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            title   TEXT NOT NULL,
            content TEXT NOT NULL,
            status  TEXT DEFAULT 'pending'
        );

        CREATE TABLE reviewers (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT NOT NULL,
            email            TEXT NOT NULL UNIQUE,
            max_workload     INTEGER DEFAULT 5,
            current_workload INTEGER DEFAULT 0,
            conflict_subject TEXT DEFAULT ''
        );

        CREATE TABLE reviews (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            submission_id INTEGER NOT NULL,
            reviewer_id   INTEGER NOT NULL,
            score         INTEGER NOT NULL,
            comment       TEXT,
            FOREIGN KEY (submission_id) REFERENCES submissions(id),
            FOREIGN KEY (reviewer_id)   REFERENCES reviewers(id)
        );
    """)

    reviewers = [
        ("Alice",  "alice@example.com",  5, 0, "AI"),
        ("Bob",    "bob@example.com",    5, 2, "ML"),
        ("Carol",  "carol@example.com",  3, 1, ""),
        ("David",  "david@example.com",  4, 0, "Security"),
        ("Eve",    "eve@example.com",    5, 3, ""),
    ]
    cursor.executemany("""
        INSERT INTO reviewers (name, email, max_workload, current_workload, conflict_subject)
        VALUES (?, ?, ?, ?, ?)
    """, reviewers)

    conn.commit()
    conn.close()
    print(f"Database '{DB_NAME}' created and seeded.")

if __name__ == "__main__":
    setup_database()