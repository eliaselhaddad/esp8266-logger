ingest_enabled = True
ingest_interval_seconds = 2


def is_ingest_enabled():
    return ingest_enabled


def get_ingest_interval_seconds():
    return ingest_interval_seconds


def start_ingest():
    global ingest_enabled
    ingest_enabled = True


def stop_ingest():
    global ingest_enabled
    ingest_enabled = False


def set_ingest_interval_seconds(seconds: int):
    global ingest_interval_seconds
    ingest_interval_seconds = max(1, min(seconds, 60))

