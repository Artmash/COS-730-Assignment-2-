import sqlite3
from dataclasses import dataclass
from typing import List, Dict

DB_NAME = "submission_review.db"

@dataclass
class Submission:
    id: int
    title: str
    content: str
    status: str

@dataclass
class Reviewer:
    id: int
    name: str
    email: str
    current_workload: int
    max_workload: int
    conflict_subject: str

class SubmissionRepository:
    @staticmethod
    def save(title: str, content: str) -> int:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO submissions (title, content, status) VALUES (?, ?, ?)",
            (title, content, "submitted"),
        )
        submission_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return submission_id

class ReviewerRepository:
    @staticmethod
    def get_available_reviewers(submission_title: str = "") -> List[Reviewer]:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, email, current_workload, max_workload, conflict_subject FROM reviewers"
        )
        rows = cursor.fetchall()
        conn.close()

        available = []
        title_lower = submission_title.lower()
        for row in rows:
            rev = Reviewer(
                id=row[0],
                name=row[1],
                email=row[2],
                current_workload=row[3],
                max_workload=row[4],
                conflict_subject=row[5] or "",
            )
            if rev.current_workload >= rev.max_workload:
                continue
            if rev.conflict_subject and rev.conflict_subject.lower() in title_lower:
                continue
            available.append(rev)
        return available

    @staticmethod
    def save_scores_batch(submission_id: int, reviewer_scores: List[tuple]) -> None:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO reviews (submission_id, reviewer_id, score) VALUES (?, ?, ?)",
            [(submission_id, rid, score) for rid, score in reviewer_scores],
        )
        conn.commit()
        conn.close()

    @staticmethod
    def update_workload_batch(reviewer_ids: List[int]) -> None:
        if not reviewer_ids:
            return
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.executemany(
            "UPDATE reviewers SET current_workload = current_workload + 1 WHERE id = ?",
            [(rid,) for rid in reviewer_ids],
        )
        conn.commit()
        conn.close()

class DecisionEngine:
    ACCEPTANCE_THRESHOLD = 8.0
    REJECTION_THRESHOLD = 5.0
    CONSENSUS_SPREAD = 2

    @staticmethod
    def evaluate(scores: List[int]) -> str:
        if not scores:
            return "revision"
        avg = sum(scores) / len(scores)
        consensus = (max(scores) - min(scores)) <= DecisionEngine.CONSENSUS_SPREAD
        if avg >= DecisionEngine.ACCEPTANCE_THRESHOLD and consensus:
            return "accepted"
        if avg < DecisionEngine.REJECTION_THRESHOLD:
            return "rejected"
        return "revision"

class EvaluationCoordinator:
    def __init__(self, submission_id: int, reviewers: List[Reviewer]):
        self.submission_id = submission_id
        self.reviewers = reviewers

    def run_evaluation(self) -> str:
        reviewer_scores = []
        scores = []
        for reviewer in self.reviewers:
            score = (reviewer.id * 7) % 10 + 1
            scores.append(score)
            reviewer_scores.append((reviewer.id, score))

        if reviewer_scores:
            ReviewerRepository.save_scores_batch(self.submission_id, reviewer_scores)
            ReviewerRepository.update_workload_batch([rid for rid, _ in reviewer_scores])

        return DecisionEngine.evaluate(scores)

class Validator:
    @staticmethod
    def validate(data: Dict) -> bool:
        return bool(data.get("title") and data.get("content"))

class NotificationService:
    @staticmethod
    def notify_acceptance(researcher_email: str) -> None:
        print(f"[Optimised] Acceptance sent to {researcher_email}")

    @staticmethod
    def notify_rejection(researcher_email: str) -> None:
        print(f"[Optimised] Rejection sent to {researcher_email}")

    @staticmethod
    def notify_revision(researcher_email: str) -> None:
        print(f"[Optimised] Revision sent to {researcher_email}")

class SubmissionController:
    def submit(self, data: Dict) -> Dict:
        if not Validator.validate(data):
            return {"error": "Invalid format"}

        submission_id = SubmissionRepository.save(data["title"], data["content"])
        reviewers = ReviewerRepository.get_available_reviewers(data.get("title", ""))

        coordinator = EvaluationCoordinator(submission_id, reviewers)
        decision = coordinator.run_evaluation()

        researcher_email = data.get("email", "researcher@example.com")
        if decision == "accepted":
            NotificationService.notify_acceptance(researcher_email)
        elif decision == "rejected":
            NotificationService.notify_rejection(researcher_email)
        else:
            NotificationService.notify_revision(researcher_email)

        return {"status": decision, "submission_id": submission_id}

class UI:
    @staticmethod
    def submit(data: Dict) -> Dict:
        controller = SubmissionController()
        return controller.submit(data)

if __name__ == "__main__":
    test_data = {
        "title": "AI in SE",
        "content": "Full paper content here.",
        "email": "researcher@example.com",
    }
    result = UI.submit(test_data)
    print("Optimised result:", result)