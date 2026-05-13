import sqlite3
from typing import List, Dict

DB_NAME = "submission_review.db"

class Database:
    @staticmethod
    def save_submission(data: Dict) -> int:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO submissions (title, content, status) VALUES (?, ?, ?)",
            (data["title"], data["content"], "submitted"),
        )
        submission_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return submission_id

    @staticmethod
    def fetch_reviewers() -> List[Dict]:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, email, current_workload, max_workload, conflict_subject FROM reviewers"
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "id": r[0],
                "name": r[1],
                "email": r[2],
                "current_workload": r[3],
                "max_workload": r[4],
                "conflict_subject": r[5],
            }
            for r in rows
        ]

    @staticmethod
    def save_score(submission_id: int, reviewer_id: int, score: int) -> None:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO reviews (submission_id, reviewer_id, score) VALUES (?, ?, ?)",
            (submission_id, reviewer_id, score),
        )
        conn.commit()
        conn.close()

class Validator:
    def validate_format(self, data: Dict) -> bool:
        return bool(data.get("title") and data.get("content"))

class ReviewerManager:
    def get_available_reviewers(self) -> List[Dict]:
        db = Database()
        reviewer_list = db.fetch_reviewers()
        filtered = self.filter_conflicts(reviewer_list, "AI")
        filtered = self.check_workload(filtered)
        return filtered

    def filter_conflicts(self, reviewers: List[Dict], conflict_subject: str) -> List[Dict]:
        return [r for r in reviewers if r["conflict_subject"] != conflict_subject]

    def check_workload(self, reviewers: List[Dict]) -> List[Dict]:
        return [r for r in reviewers if r["current_workload"] < r["max_workload"]]

class Reviewer:
    def assign_review(self, submission_id: int, reviewer_id: int) -> None:
        pass

    def submit_score(
        self,
        submission_id: int,
        reviewer_id: int,
        score: int,
        eval_manager: "EvaluationManager",
    ) -> None:
        eval_manager.submit_score(score, submission_id, reviewer_id)

class EvaluationManager:
    def __init__(self) -> None:
        self.scores: List[int] = []

    def start_evaluation(self) -> None:
        self.scores = []

    def submit_score(self, score: int, submission_id: int, reviewer_id: int) -> None:
        self.scores.append(score)
        Database.save_score(submission_id, reviewer_id, score)

    def calculate_average(self) -> float:
        if not self.scores:
            return 0.0
        return sum(self.scores) / len(self.scores)

    def check_consensus(self) -> bool:
        if len(self.scores) <= 1:
            return True
        return (max(self.scores) - min(self.scores)) <= 2

    def apply_rules(self) -> str:
        avg = self.calculate_average()
        consensus = self.check_consensus()
        if avg >= 8.0 and consensus:
            return "accepted"
        elif avg < 5.0:
            return "rejected"
        else:
            return "revision"

class NotificationService:
    def notify_acceptance(self, researcher_email: str) -> None:
        print(f"[Baseline] Acceptance sent to {researcher_email}")

    def notify_rejection(self, researcher_email: str) -> None:
        print(f"[Baseline] Rejection sent to {researcher_email}")

    def notify_revision(self, researcher_email: str) -> None:
        print(f"[Baseline] Revision sent to {researcher_email}")

class SubmissionController:
    def submit(self, data: Dict) -> Dict:
        validator = Validator()
        if not validator.validate_format(data):
            return {"error": "Invalid format"}

        db = Database()
        submission_id = db.save_submission(data)

        reviewer_manager = ReviewerManager()
        reviewers = reviewer_manager.get_available_reviewers()

        for reviewer in reviewers:
            rev = Reviewer()
            rev.assign_review(submission_id, reviewer["id"])

        eval_manager = EvaluationManager()
        eval_manager.start_evaluation()

        for reviewer in reviewers:
            rev = Reviewer()
            score = (reviewer["id"] * 7) % 10 + 1
            rev.submit_score(submission_id, reviewer["id"], score, eval_manager)

        decision = eval_manager.apply_rules()

        notifier = NotificationService()
        researcher_email = data.get("email", "researcher@example.com")
        if decision == "accepted":
            notifier.notify_acceptance(researcher_email)
        elif decision == "rejected":
            notifier.notify_rejection(researcher_email)
        else:
            notifier.notify_revision(researcher_email)

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
    print("Baseline result:", result)