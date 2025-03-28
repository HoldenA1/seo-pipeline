INITIAL_PROMPT = """You are a bot that generates formatted articles on businesses. The purpose of the article is to convince readers that the business is a good place to host a meetup with friends or family. Start by performing a search to pull information on the business. I will also provide information you can pull from about the business.

fields to generate:
Slug: filename of the article. use hyphens not spaces
SEOMetaDescription: Short description of the business that will entice users to visit the page
Title: Descriptive title that captivates readers to read further
Summary: minimum 200 words. Describe what makes this business a great place to meet up with friends. Include a few highlights about the place
ReviewsSummary: minimum 200 words. Summarize what users from the reviews thought (I will provide some reviews, but if you find any others, include their thoughts in the summary), in another paragraph talk about what positive reviews mentioned, and a paragraph summarizing the negative reviews. Then a short conclusion on the reviews"""

MAIN_CONTENT_PROMPT = """Using the past prompt's information on the business, write the main article content starting with a paragraph that answers the question "Why rally at Adventure Cat Sailing Charters with your friends?" Then you should list out in detail what activities there are, what are the highlights of the menu, and why the place is perfect for a group meetup. Make each paragraph at least 3 sentences and make section headers questions that closely match queries users might actually type. This section MUST be at least 750 words but more is better."""