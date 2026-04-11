from __future__ import annotations

QUESTION_BANK = [
    # Technical — Coding (5)
    {
        "id": 1,
        "category": "coding",
        "category_type": "technical",
        "difficulty": "easy",
        "text": "What is the time complexity of looking up a value by key in a Python dictionary on average?",
        "options": ["O(n)", "O(log n)", "O(1)", "O(n log n)"],
        "correct_index": 2,
        "explanation": "Python dictionaries use a hash table, so average lookup is constant time."
    },
    {
        "id": 2,
        "category": "coding",
        "category_type": "technical",
        "difficulty": "easy",
        "text": "Which HTTP method is typically used to update an existing resource?",
        "options": ["GET", "POST", "PUT", "TRACE"],
        "correct_index": 2,
        "explanation": "PUT is commonly used to update or replace an existing resource."
    },
    {
        "id": 3,
        "category": "coding",
        "category_type": "technical",
        "difficulty": "medium",
        "text": "Which SQL clause is used to filter grouped results after aggregation?",
        "options": ["WHERE", "HAVING", "ORDER BY", "LIMIT"],
        "correct_index": 1,
        "explanation": "HAVING filters results after GROUP BY aggregation."
    },
    {
        "id": 4,
        "category": "coding",
        "category_type": "technical",
        "difficulty": "medium",
        "text": "What does JSON stand for?",
        "options": ["Java Source Object Notation", "JavaScript Object Notation", "Joined Syntax Open Network", "Java Serialized Output Name"],
        "correct_index": 1,
        "explanation": "JSON stands for JavaScript Object Notation."
    },
    {
        "id": 5,
        "category": "coding",
        "category_type": "technical",
        "difficulty": "medium",
        "text": "Which data structure works on a Last-In, First-Out principle?",
        "options": ["Queue", "Heap", "Stack", "Graph"],
        "correct_index": 2,
        "explanation": "A stack removes the most recently added element first."
    },

    # Technical — Finance (5)
    {
        "id": 6,
        "category": "finance",
        "category_type": "technical",
        "difficulty": "easy",
        "text": "Revenue minus expenses equals:",
        "options": ["Assets", "Profit", "Equity", "Liability"],
        "correct_index": 1,
        "explanation": "Profit is what remains after subtracting expenses from revenue."
    },
    {
        "id": 7,
        "category": "finance",
        "category_type": "technical",
        "difficulty": "easy",
        "text": "Which financial statement shows a company's assets, liabilities, and equity?",
        "options": ["Cash Flow Statement", "Income Statement", "Balance Sheet", "Sales Report"],
        "correct_index": 2,
        "explanation": "The balance sheet summarizes assets, liabilities, and equity."
    },
    {
        "id": 8,
        "category": "finance",
        "category_type": "technical",
        "difficulty": "medium",
        "text": "If an investment grows from ₹10,000 to ₹11,000, what is the return percentage?",
        "options": ["5%", "10%", "11%", "20%"],
        "correct_index": 1,
        "explanation": "The gain is ₹1,000 on ₹10,000, which is 10%."
    },
    {
        "id": 9,
        "category": "finance",
        "category_type": "technical",
        "difficulty": "medium",
        "text": "Which metric is commonly used to evaluate profitability relative to revenue?",
        "options": ["Gross margin", "Burn rate", "Runway", "Headcount ratio"],
        "correct_index": 0,
        "explanation": "Gross margin compares gross profit to revenue."
    },
    {
        "id": 10,
        "category": "finance",
        "category_type": "technical",
        "difficulty": "medium",
        "text": "A budget variance means:",
        "options": ["The difference between expected and actual values", "A tax deduction", "A type of asset", "An accounting standard"],
        "correct_index": 0,
        "explanation": "Variance compares actual performance against budgeted numbers."
    },

    # Technical — Marketing (5)
    {
        "id": 11,
        "category": "marketing",
        "category_type": "technical",
        "difficulty": "easy",
        "text": "CTR in digital marketing stands for:",
        "options": ["Customer Trend Rate", "Click-Through Rate", "Content Traffic Reach", "Campaign Time Ratio"],
        "correct_index": 1,
        "explanation": "CTR measures the percentage of viewers who click an ad or link."
    },
    {
        "id": 12,
        "category": "marketing",
        "category_type": "technical",
        "difficulty": "easy",
        "text": "Which metric best measures how many visitors complete a desired action?",
        "options": ["Bounce rate", "Conversion rate", "Impression share", "Follower count"],
        "correct_index": 1,
        "explanation": "Conversion rate tracks the percentage of users who complete a target action."
    },
    {
        "id": 13,
        "category": "marketing",
        "category_type": "technical",
        "difficulty": "medium",
        "text": "A/B testing is mainly used to:",
        "options": ["Track employee attendance", "Compare two versions to see which performs better", "Set ad budgets automatically", "Archive campaign assets"],
        "correct_index": 1,
        "explanation": "A/B testing compares two variants to determine which performs better."
    },
    {
        "id": 14,
        "category": "marketing",
        "category_type": "technical",
        "difficulty": "medium",
        "text": "Which funnel stage usually comes right after awareness?",
        "options": ["Advocacy", "Retention", "Consideration", "Churn"],
        "correct_index": 2,
        "explanation": "A common customer journey moves from awareness to consideration."
    },
    {
        "id": 15,
        "category": "marketing",
        "category_type": "technical",
        "difficulty": "medium",
        "text": "CAC refers to:",
        "options": ["Customer Acquisition Cost", "Content Accuracy Check", "Campaign Allocation Curve", "Creative Approval Cycle"],
        "correct_index": 0,
        "explanation": "CAC is the cost of acquiring a customer."
    },

    # Technical — Design (4)
    {
        "id": 16,
        "category": "design",
        "category_type": "technical",
        "difficulty": "easy",
        "text": "Which principle helps make interface elements feel related to one another?",
        "options": ["Randomization", "Proximity", "Blur", "Animation"],
        "correct_index": 1,
        "explanation": "Proximity groups related items visually."
    },
    {
        "id": 17,
        "category": "design",
        "category_type": "technical",
        "difficulty": "easy",
        "text": "What is the main goal of wireframing?",
        "options": ["Finalize color palette", "Plan layout and structure early", "Export production assets", "Compress images"],
        "correct_index": 1,
        "explanation": "Wireframes focus on structure and layout before visual polish."
    },
    {
        "id": 18,
        "category": "design",
        "category_type": "technical",
        "difficulty": "medium",
        "text": "Which color contrast practice improves accessibility?",
        "options": ["Low contrast text on bright backgrounds", "Using text and background with strong luminance difference", "Using only pastel colors", "Removing labels from forms"],
        "correct_index": 1,
        "explanation": "Accessible interfaces use sufficient contrast between text and background."
    },
    {
        "id": 19,
        "category": "design",
        "category_type": "technical",
        "difficulty": "medium",
        "text": "A design system is best described as:",
        "options": ["A single landing page", "A set of reusable components and guidelines", "Only a logo pack", "A feedback survey"],
        "correct_index": 1,
        "explanation": "Design systems provide repeatable components, rules, and patterns."
    },

    # Technical — Data Science (5)
    {
        "id": 20,
        "category": "data_science",
        "category_type": "technical",
        "difficulty": "easy",
        "text": "Which measure represents the average value of a dataset?",
        "options": ["Median", "Mode", "Mean", "Range"],
        "correct_index": 2,
        "explanation": "Mean is the arithmetic average."
    },
    {
        "id": 21,
        "category": "data_science",
        "category_type": "technical",
        "difficulty": "easy",
        "text": "What is overfitting in machine learning?",
        "options": ["A model that performs well on training data but poorly on new data", "A model that is too small to train", "Deleting too many rows from a dataset", "Using only one feature"],
        "correct_index": 0,
        "explanation": "Overfitting happens when a model memorizes training data instead of learning general patterns."
    },
    {
        "id": 22,
        "category": "data_science",
        "category_type": "technical",
        "difficulty": "medium",
        "text": "Which chart is best for showing a trend over time?",
        "options": ["Pie chart", "Line chart", "Tree map", "Scatter plot only"],
        "correct_index": 1,
        "explanation": "Line charts are commonly used to show changes over time."
    },
    {
        "id": 23,
        "category": "data_science",
        "category_type": "technical",
        "difficulty": "medium",
        "text": "What does a confusion matrix help evaluate?",
        "options": ["Database speed", "Classification model performance", "Website color themes", "Cloud storage usage"],
        "correct_index": 1,
        "explanation": "A confusion matrix shows actual vs predicted classes for a classifier."
    },
    {
        "id": 24,
        "category": "data_science",
        "category_type": "technical",
        "difficulty": "medium",
        "text": "Which step should usually happen before model training?",
        "options": ["Ignore missing values", "Clean and preprocess the data", "Publish the dashboard", "Delete all outliers automatically"],
        "correct_index": 1,
        "explanation": "Preparing and cleaning data is a standard step before training a model."
    },

    # Soft Skills (6)
    {
        "id": 25,
        "category": "communication",
        "category_type": "soft",
        "difficulty": "easy",
        "text": "A strong way to handle unclear instructions is to:",
        "options": ["Stay silent and guess", "Ask clarifying questions early", "Wait until the deadline passes", "Blame the team"],
        "correct_index": 1,
        "explanation": "Clarifying expectations early reduces mistakes and rework."
    },
    {
        "id": 26,
        "category": "teamwork",
        "category_type": "soft",
        "difficulty": "easy",
        "text": "In a team conflict, the best first step is usually to:",
        "options": ["Escalate immediately", "Ignore the issue", "Understand each person's perspective", "Leave the project"],
        "correct_index": 2,
        "explanation": "Understanding perspectives helps resolve conflict constructively."
    },
    {
        "id": 27,
        "category": "time_management",
        "category_type": "soft",
        "difficulty": "medium",
        "text": "When several tasks are due soon, the best approach is to:",
        "options": ["Do the easiest task first every time", "Prioritize by urgency and impact", "Work randomly", "Delay communication"],
        "correct_index": 1,
        "explanation": "Prioritizing by urgency and impact is a practical time management habit."
    },
    {
        "id": 28,
        "category": "adaptability",
        "category_type": "soft",
        "difficulty": "medium",
        "text": "A project requirement changes suddenly. A good response is to:",
        "options": ["Refuse all changes", "Assess impact and adjust plan", "Pretend nothing changed", "Restart from zero without review"],
        "correct_index": 1,
        "explanation": "Adaptability means evaluating the change and adjusting rationally."
    },
    {
        "id": 29,
        "category": "professionalism",
        "category_type": "soft",
        "difficulty": "easy",
        "text": "If you may miss a deadline, what should you do first?",
        "options": ["Hide it until the due date", "Inform the stakeholder early and propose a plan", "Stop working on it", "Delete the task"],
        "correct_index": 1,
        "explanation": "Early communication and a recovery plan show professionalism."
    },
    {
        "id": 30,
        "category": "problem_solving",
        "category_type": "soft",
        "difficulty": "medium",
        "text": "What is the best way to approach a new problem you have not seen before?",
        "options": ["Panic and switch tasks", "Break it into smaller parts and test assumptions", "Wait for someone else to solve it", "Copy the first answer online"],
        "correct_index": 1,
        "explanation": "Breaking a problem into parts is a core problem-solving technique."
    },
]
