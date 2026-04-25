# Legal Document Templates
# Contains templates for FIR, complaints, RTI, etc.

CONSUMER_COMPLAINT_TEMPLATE = """
To,
The District Consumer Disputes Redressal Commission
[Address]

Date: [DATE]

Subject: Complaint under Section 35 of the Consumer Protection Act, 2019

Sir/Madam,

I hereby file a complaint against [DEFENDANT NAME] (Address: [ADDRESS]) for the following violations:

1. DEFICIENCY IN SERVICE / DEFECTIVE PRODUCT
   [Describe the issue in detail]

2. RELIEF SOUGHT
   [a] Refund of Rs. [AMOUNT]
   [b] Compensation for mental agony Rs. [AMOUNT]
   [c] Cost of litigation

3. FACTS OF THE CASE
   [Brief facts with dates]

4. DOCUMENTS ATTACHED
   - Copy of Bill/Receipt
   - Correspondence with seller
   - [Other documents]

I certify that the above information is true to the best of my knowledge.

Sincerely,
[COMPLAINANT NAME]
Address: [ADDRESS]
Phone: [PHONE]
"""

FIR_TEMPLATE = """
To,
The Station House Officer
[POLICE STATION NAME]
[Address]

Date: [DATE]

Subject: Request to register an FIR under Section [SECTION] of Indian Penal Code

Sir,

I request your good self to register an FIR for the following incident:

1. DATE, TIME & PLACE
   [When and where did the incident occur]

2. DETAILS OF OCCURRENCE
   [What happened - describe in detail]

3. NAME AND DESCRIPTION OF ACCUSED
   [If known]

4. WITNESSES
   [If any]

5. EVIDENCE
   [Physical evidence, documents, etc.]

6. DAMAGES/ LOSS SUFFERED
   [Details]

I request appropriate action under law.

Sincerely,
[COMPLAINANT NAME]
Address: [ADDRESS]
Phone: [PHONE]
"""

RTI_TEMPLATE = """
To,
The Public Information Officer
[DEPARTMENT NAME]
[ADDRESS]

Date: [DATE]

Subject: Application under Right to Information Act, 2005

Sir,

I request the following information under RTI Act, 2005:

1. [Specific query 1]
2. [Specific query 2]
3. [Specific query 3]

I enclose Rs. [AMOUNT] as RTI fee via [DD/IPO/Online].

Please provide information within 30 days as per Section 7(1) of RTI Act.

Sincerely,
[APPLICANT NAME]
Address: [ADDRESS]
Phone: [PHONE]
"""

LABOUR_COMPLAINT_TEMPLATE = """
To,
The Labour Commissioner
[DISTRICT]
[Address]

Date: [DATE]

Subject: Complaint under the Industrial Disputes Act, 1947 / Payment of Wages Act

Sir,

I am submitting this complaint against my employer [COMPANY NAME] for:

1. UNLAWFUL TERMINATION / NON-PAYMENT OF WAGES
   [Describe issue]

2. RELIEF SOUGHT
   [a] Reinstatement with full back wages
   [b] Payment of pending wages Rs. [AMOUNT]
   [c] Other relief

3. EMPLOYMENT DETAILS
   - Designation: [ROLE]
   - Date of joining: [DATE]
   - Salary: Rs. [AMOUNT] per month

4. DOCUMENTS ATTACHED
   - Appointment letter
   - Salary slips
   - Termination letter
   - [Other documents]

I request your kind intervention.

Sincerely,
[COMPLAINANT NAME]
Address: [ADDRESS]
Phone: [PHONE]
"""

def get_template(template_type: str) -> str:
    templates = {
        "consumer_complaint": CONSUMER_COMPLAINT_TEMPLATE,
        "fir": FIR_TEMPLATE,
        "rti": RTI_TEMPLATE,
        "labour_complaint": LABOUR_COMPLAINT_TEMPLATE,
    }
    return templates.get(template_type, CONSUMER_COMPLAINT_TEMPLATE)