import pandas as pd
import re

INPUT_FILE = "bangalore_emails_new.csv"
OUTPUT_FILE = "bangalore_final.csv"


def clean_phone(phone):
    if pd.isna(phone):
        return ""
    return re.sub(r"\D", "", str(phone))


def clean_csv(input_file, output_file):

    df = pd.read_csv(input_file)

    print("Rows before cleaning:", len(df))

    # normalize phone (in place)
    df["phone"] = df["phone"].apply(clean_phone)

    # make ratings numeric
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["ratings_count"] = pd.to_numeric(df["ratings_count"], errors="coerce")

    # sort best first
    df = df.sort_values(
        by=["rating", "ratings_count"],
        ascending=[False, False]
    )

    # remove duplicate phones
    df = df.drop_duplicates(subset=["phone"], keep="first")

    # save
    df.to_csv(output_file, index=False, quoting=1)

    print("Rows after cleaning:", len(df))
    print("Saved →", output_file)


if __name__ == "__main__":
    clean_csv(INPUT_FILE, OUTPUT_FILE)
