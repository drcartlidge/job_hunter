def baseline_title_filter(job: Job) -> bool:
    KEYWORDS = [
        "data","machine","ml","ai","analytics","insights","quant","science",
        "research scientist","measurement","psychometric","assessment","statistician"
    ]
    title = job.title.lower()
    if any(k in title for k in KEYWORDS):
        return True
    if "researcher" in title and any(x in title for x in ["data","quant","ml","ai","analytics","psychometric","assessment"]):
        return True
    return False
