import openmed
print("openmed version:", getattr(openmed, "__version__", "?"))
t = "病患姓名：王大明，身分證字號 A123456789，電話 0912-345-678，生日 1985-05-12，病歷號 MRN-998822。"
res = openmed.extract_pii(t, lang="zh", use_smart_merging=True)
for e in res.entities:
    print("ENTITY:", e.label, repr(e.text), e.start, e.end, getattr(e, "confidence", None))
d = openmed.deidentify(t, method="mask", lang="zh")
print("DEID:", d.deidentified_text)
