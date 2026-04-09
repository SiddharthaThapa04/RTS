def build_ndf_record(title: str) -> dict:
    """
    Build a standard fallback record for movies that could not be found.

    `NDF` is used here as a placeholder value meaning "No Data Found".
    This keeps the database output structurally consistent even when a movie
    cannot be matched or scraped successfully.
    """
    return {
        "title": title,
        "year": -1,
        "tomatometer": "NDF",
        "audience_score": "NDF",
        "storyline": "NDF",
        "genre": "NDF",
        "runtime": "NDF",
        "rating": "NDF",
        "release_date": "NDF",
        "critic_1": "NDF",
        "critic_2": "NDF",
        "critic_3": "NDF",
        "critic_4": "NDF",
        "critic_5": "NDF",
        "critic_6": "NDF",
    }
