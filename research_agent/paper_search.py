import arxiv

def test():
    client = arxiv.Client()

    search = arxiv.Search(
        query="large language model",
        max_results=5,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    results = client.results(search)

    for r in results:
        print("\n" + "=" * 50)
        print(r.title)
        print(", ".join([a.name for a in r.authors]))
        print(r.summary[:300])


if __name__ == "__main__":
    test()