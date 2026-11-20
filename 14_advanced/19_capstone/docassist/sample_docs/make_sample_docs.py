# Writes the two sample PDFs that DocAssist answers questions about.
# Run once (the PDFs are already in this folder): python make_sample_docs.py
# BlueRiver Software is a made-up company.
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LEAVE = ("BlueRiver Software - Leave Policy", [
    ("Annual leave", "Full-time employees get 18 days of annual leave per calendar "
     "year, earned at 1.5 days per month. Up to 10 unused days can be carried forward "
     "to the next year. Days above 10 lapse on 31 March. Annual leave must be applied "
     "for on the HR portal at least 7 days in advance and approved by your manager."),
    ("Casual leave", "Employees get 8 days of casual leave per year for personal "
     "matters. Casual leave cannot be carried forward and cannot be taken for more "
     "than 3 days in a row."),
    ("Sick leave", "Employees get 10 days of sick leave per year. A medical "
     "certificate is required for sick leave of more than 2 days in a row."),
    ("Part-time employees and interns", "Part-time employees get annual leave in "
     "proportion to their working hours: an employee working 3 days a week gets "
     "60 percent of 18 days, that is 10.8 days, rounded up to 11. Interns get 1 day of "
     "leave per month of internship and cannot carry leave forward."),
    ("Public holidays and compensatory off", "The company observes 10 public holidays "
     "a year, published on the HR portal in December. An employee who works on a "
     "public holiday, or travels for work on one, gets one compensatory day off, "
     "which must be taken within 30 days."),
])

TRAVEL = ("BlueRiver Software - Travel and Expense Policy", [
    ("Flights", "Domestic flights are booked in economy class through the travel desk. "
     "Business class is allowed only for flights longer than 6 hours, with written "
     "approval from a Vice President."),
    ("Hotels", "The maximum hotel rate per night is INR 7,000 in Mumbai and Delhi, "
     "INR 5,500 in Bengaluru, Pune and Hyderabad, and INR 4,000 in all other cities. "
     "Any amount above the limit is paid by the employee."),
    ("Daily allowance", "Employees get a daily allowance of INR 1,200 for meals and "
     "local expenses on every day of travel. No receipts are needed for the daily "
     "allowance."),
    ("Local travel", "Taxis and app cabs are reimbursed at actual cost. Use of a "
     "personal car is reimbursed at INR 12 per kilometre."),
    ("Advances and claims", "An advance of up to 60 percent of the estimated trip cost "
     "can be requested from Finance. Expense claims must be submitted on the expense "
     "portal within 15 days of returning. Receipts are required for every expense "
     "above INR 500. Late claims need approval from the department head."),
    ("Travel on holidays", "Travelling for work on a weekend or a public holiday "
     "earns compensatory time off as described in the Leave Policy."),
])


def write_pdf(file_name, title, sections):
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
    for heading, text in sections:
        story.append(Paragraph(heading, styles["Heading2"]))
        story.append(Paragraph(text, styles["BodyText"]))
    SimpleDocTemplate(os.path.join(BASE_DIR, file_name), pagesize=A4).build(story)
    print("wrote", file_name)


write_pdf("leave_policy.pdf", *LEAVE)
write_pdf("travel_policy.pdf", *TRAVEL)
