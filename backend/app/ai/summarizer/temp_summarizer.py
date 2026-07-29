from summarizer import DocumentSummarizer


summarizer = DocumentSummarizer()


sample_text = """
Artificial Intelligence (AI) has become one of the fastest-growing fields
in computer science.

Machine Learning enables computers to learn patterns from data without
being explicitly programmed.

Deep Learning extends this capability through neural networks containing
multiple hidden layers.

Today AI is widely used in healthcare, finance, autonomous vehicles,
robotics, education, cybersecurity, manufacturing and scientific research.

Despite its advantages, AI also raises ethical concerns regarding bias,
privacy, transparency and responsible deployment.
"""


result = summarizer.summarize(sample_text)

print("\n========== SUMMARY ==========\n")

print(result["summary"])