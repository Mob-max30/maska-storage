from cleaner import TextCleaner

cleaner = TextCleaner()

raw_text = """
        Hello          World!





This\t\tis     a    cleaner.


Python      is      awesome.


"""


print("========== BEFORE ==========\n")
print(raw_text)

cleaned = cleaner.clean(raw_text)

print("\n========== AFTER ==========\n")
print(cleaned)