# models.py
class Job:
    def __init__(self, title, company):
        self.title = title
        self.company = company

    def __repr__(self):
        return f"<Job {self.title} at {self.company}>"
