/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useMemo, useReducer } from 'react'

/**
 * LegalDataContext — Fully hardcoded legal assistance data.
 * No backend needed. All demo data lives here.
 */

const LegalContext = createContext(null)

// ── Hardcoded demo data ──────────────────────────
const DEMO_CHAT_RESPONSES = {
  'fir': {
    answer: `**How to File an FIR (First Information Report):**\n\n1. **Visit the nearest police station** — Go to the police station that has jurisdiction over the area where the crime occurred.\n\n2. **Provide details verbally or in writing** — You can narrate the incident to the Station House Officer (SHO). They are legally obligated to register your FIR under Section 154 of CrPC.\n\n3. **Information to include:**\n   - Your name and address\n   - Date, time, and place of the incident\n   - Description of the incident\n   - Names of the accused (if known)\n   - Names of witnesses\n   - Details of property stolen/damaged\n\n4. **Get a free copy** — Under Section 154(2) of CrPC, you are entitled to a free copy of the FIR.\n\n5. **Zero FIR** — You can file an FIR at ANY police station regardless of jurisdiction. The police must register it and then transfer it to the correct station.\n\n**Your Rights:**\n- The police CANNOT refuse to register an FIR for a cognizable offence.\n- If they refuse, you can send your complaint to the Superintendent of Police (SP) by post.\n- You can also approach a Magistrate under Section 156(3) of CrPC.`,
    category: 'Criminal Law',
    confidence: 95,
    relatedSections: ['Section 154 CrPC', 'Section 156(3) CrPC', 'Section 190 CrPC'],
  },
  'consumer': {
    answer: `**Filing a Consumer Complaint:**\n\nUnder the **Consumer Protection Act, 2019**, you can file a complaint if you've been cheated or received defective goods/services.\n\n**Step-by-Step Process:**\n\n1. **Send a legal notice** — Write to the company/seller describing the defect and demanding resolution within 15-30 days.\n\n2. **Choose the right forum based on claim value:**\n   - Up to ₹1 Crore → District Consumer Forum\n   - ₹1 Crore to ₹10 Crore → State Consumer Commission\n   - Above ₹10 Crore → National Consumer Commission\n\n3. **Draft the complaint including:**\n   - Your details and the opposite party's details\n   - Facts of the case\n   - Relief sought (refund, replacement, compensation)\n   - Supporting documents (bills, receipts, photos)\n\n4. **File online or offline:**\n   - Online: Visit edaakhil.nic.in\n   - Offline: Submit at the relevant forum\n\n**Key Rights:**\n- No advocate needed — you can argue your own case\n- Filing fee is minimal (₹100 to ₹5,000 based on claim)\n- Complaints must be resolved within 3-5 months`,
    category: 'Consumer Law',
    confidence: 92,
    relatedSections: ['Consumer Protection Act, 2019', 'Section 35', 'Section 69'],
  },
  'rti': {
    answer: `**How to File an RTI (Right to Information) Application:**\n\n**Step 1: Identify the Public Authority**\nDetermine which government department/body holds the information you need.\n\n**Step 2: Write Your Application**\n- Address it to the Public Information Officer (PIO)\n- Write "Application under RTI Act, 2005" at the top\n- Clearly state what information you need\n- You don't need to give a reason WHY you need it\n\n**Step 3: Pay the Fee**\n- ₹10 for Central Government (₹10 postal order/DD)\n- Varies for State Governments (usually ₹10-₹50)\n- BPL cardholders are exempt from fees\n\n**Step 4: Submit**\n- Online: rtionline.gov.in (for central departments)\n- By post or in person at the relevant office\n\n**Timelines:**\n- Reply must come within **30 days**\n- Life/liberty matters: **48 hours**\n- If transferred to another department: **35 days**\n\n**If Denied:**\nFile a First Appeal with the Appellate Authority within 30 days, then Second Appeal with the Central/State Information Commission.`,
    category: 'Right to Information',
    confidence: 97,
    relatedSections: ['RTI Act, 2005', 'Section 6', 'Section 7', 'Section 19'],
  },
  'rental': {
    answer: `**Understanding Your Rental Agreement — Key Red Flags:**\n\n**Common Issues to Watch For:**\n\n1. **Lock-in Period** — Check if there's a clause preventing you from leaving early. Typical lock-in is 11 months. If you leave early, you may lose your deposit.\n\n2. **Security Deposit** — The legal norm is 1-2 months' rent. Some landlords demand 6-10 months — this is excessive and sometimes illegal under state rent control laws.\n\n3. **Maintenance Charges** — Clarify what's included. Major structural repairs are the landlord's responsibility under Section 108 of the Transfer of Property Act.\n\n4. **Eviction Clause** — Landlord must give adequate notice (usually 1-3 months). "Immediate eviction" clauses may not be enforceable.\n\n5. **Rent Escalation** — Annual increases above 5-10% are unusual. Check if there's an escalation cap.\n\n**Your Protections:**\n- Rent Control Acts (state-specific) protect against unreasonable eviction\n- Receipts for rent paid are legally required on request\n- A registered agreement (for 12+ months) gives stronger legal protection\n- Police cannot evict you — only a court order can`,
    category: 'Property Law',
    confidence: 88,
    relatedSections: ['Transfer of Property Act, Section 108', 'State Rent Control Acts', 'Registration Act, 1908'],
  },
  'workplace': {
    answer: `**Workplace Harassment / Unfair Treatment — Your Legal Options:**\n\n**1. Internal Complaints Committee (ICC)**\nUnder the **POSH Act, 2013** (Prevention of Sexual Harassment), every organization with 10+ employees must have an ICC. File a written complaint within 3 months of the incident.\n\n**2. Labour Commissioner**\nFor wage-related issues, unpaid overtime, or wrongful termination:\n- File a complaint with the Labour Commissioner\n- Under the **Industrial Disputes Act**, you're protected from unfair dismissal\n\n**3. Equal Remuneration**\nUnder the **Equal Remuneration Act, 1976**, men and women must receive equal pay for equal work.\n\n**4. Documenting Evidence**\n- Save emails, messages, and recordings (where legally permissible)\n- Keep copies of your employment contract\n- Note dates, times, and witnesses\n\n**5. Legal Remedies:**\n- File a complaint with the **National Human Rights Commission (NHRC)**\n- Approach **Women's Commission** for gender-based issues\n- File a **police complaint** if the behavior constitutes a criminal offence\n\n**Key Timeline:** Most complaints must be filed within 3-6 months of the incident.`,
    category: 'Labour & Employment Law',
    confidence: 90,
    relatedSections: ['POSH Act, 2013', 'Industrial Disputes Act', 'Equal Remuneration Act, 1976'],
  },
}

const DEMO_CASE_ANALYSIS = {
  title: 'Consumer Complaint — Defective Electronic Product',
  summary: 'Based on your description, you purchased a laptop that developed a hardware defect within the warranty period. The seller refused to honor the warranty and directed you to contact the manufacturer, who also delayed resolution. This constitutes deficiency in service and unfair trade practice under the Consumer Protection Act, 2019.',
  caseStrength: 85,
  category: 'Consumer Protection',
  applicableLaws: [
    { law: 'Consumer Protection Act, 2019', sections: ['Section 2(6) - Defect', 'Section 2(11) - Deficiency', 'Section 35 - Jurisdiction'] },
    { law: 'Sale of Goods Act, 1930', sections: ['Section 16 - Implied conditions as to quality'] },
  ],
  recommendations: [
    { step: 'Send a legal notice to both seller and manufacturer demanding replacement or full refund within 15 days', priority: 'high', deadline: 'Immediately' },
    { step: 'Collect all documents: purchase bill, warranty card, email correspondence, complaint logs', priority: 'high', deadline: '2 days' },
    { step: 'File complaint on edaakhil.nic.in (District Consumer Forum) if no response to legal notice', priority: 'medium', deadline: '30 days' },
    { step: 'Claim additional compensation for mental agony and litigation costs', priority: 'medium', deadline: 'At filing' },
  ],
  evidenceNeeded: [
    'Original purchase receipt/invoice',
    'Warranty card or warranty terms',
    'Email/SMS correspondence with seller and manufacturer',
    'Photos/videos of the defect',
    'Service center visit receipts',
    'Legal notice sent (with postal receipt)',
  ],
  estimatedResolution: '3-5 months via consumer forum',
  estimatedCost: '₹100 - ₹5,000 (filing fee only)',
}

const DEMO_DOCUMENTS = {
  legalNotice: `LEGAL NOTICE

To,
[Seller/Company Name]
[Address]

Subject: Legal Notice for Defective Product and Deficiency in Service

Dear Sir/Madam,

Under the instructions of my client [Your Name], resident of [Your Address], I hereby serve upon you the following Legal Notice:

1. That my client purchased [Product Name] bearing Serial No. [XXX] from your establishment on [Date] for a consideration of ₹[Amount].

2. That the said product developed [describe defect] within [X] months of purchase, which is well within the warranty period of [X] months/years.

3. That my client approached your service center on [Date] and was informed that [reason for denial]. This constitutes "deficiency in service" under Section 2(11) of the Consumer Protection Act, 2019.

4. That despite repeated requests on [Dates], you have failed to provide any satisfactory resolution, causing severe inconvenience and mental agony to my client.

THEREFORE, you are hereby called upon to:
(a) Replace the defective product with a new one of the same specifications, OR
(b) Refund the full purchase price of ₹[Amount],
along with compensation of ₹[Amount] for mental agony and inconvenience.

This notice must be complied with within 15 days of receipt. Failing which, my client shall be constrained to initiate appropriate legal proceedings before the Consumer Forum, at your risk and cost.

[Your Name]
[Date]`,
  rtiApplication: `APPLICATION UNDER RIGHT TO INFORMATION ACT, 2005

To,
The Public Information Officer
[Department Name]
[Address]

Subject: Request for Information under RTI Act, 2005

Sir/Madam,

I, [Your Name], resident of [Your Address], hereby seek the following information under the Right to Information Act, 2005:

1. [Specific information sought - Point 1]
2. [Specific information sought - Point 2]
3. [Specific information sought - Point 3]

I am willing to pay the prescribed fee. Kindly provide the information within the stipulated time period of 30 days as per Section 7(1) of the RTI Act, 2005.

If the requested information pertains to the life or liberty of a person, kindly provide the same within 48 hours as mandated under Section 7(1) of the Act.

Fee: ₹10 (Ten Rupees) via [Indian Postal Order No. / DD No. / Online Payment Reference]

Thanking you,
[Your Name]
[Contact Details]
[Date]`,
  complaint: `COMPLAINT BEFORE THE DISTRICT CONSUMER DISPUTES REDRESSAL FORUM

CONSUMER COMPLAINT NO. ______ OF 2024

[Your Name]                                    ... Complainant
   Vs.
[Opposite Party Name]                           ... Opposite Party

COMPLAINT UNDER SECTION 35 OF THE CONSUMER PROTECTION ACT, 2019

The complainant respectfully submits as under:

1. That the complainant is a consumer within the meaning of Section 2(7) of the Consumer Protection Act, 2019, having purchased goods/availed services from the opposite party.

2. [Facts of the case in chronological order]

3. That the above acts of the opposite party amount to:
   (a) Deficiency in Service as defined under Section 2(11)
   (b) Unfair Trade Practice as defined under Section 2(47)
   (c) Defect in Goods as defined under Section 2(6)

4. That the complainant has suffered loss/damage to the tune of ₹[Amount] on account of the above.

PRAYER:
It is therefore prayed that this Hon'ble Forum may be pleased to:
(a) Direct the opposite party to [specific relief sought]
(b) Award compensation of ₹[Amount] for mental agony
(c) Award litigation costs

[Your Name]
[Date]
[Verification and Affidavit]`,
}

const initialState = {
  chatMessages: [],
  isTyping: false,
  caseAnalysis: null,
  documents: {},
  activeDocument: null,
  currentFeature: null,
}

function reducer(state, action) {
  switch (action.type) {
    case 'ADD_USER_MESSAGE':
      return {
        ...state,
        chatMessages: [...state.chatMessages, { role: 'user', content: action.payload, timestamp: new Date().toISOString() }],
      }
    case 'SET_TYPING':
      return { ...state, isTyping: action.payload }
    case 'ADD_AI_MESSAGE':
      return {
        ...state,
        chatMessages: [...state.chatMessages, { role: 'ai', ...action.payload, timestamp: new Date().toISOString() }],
        isTyping: false,
      }
    case 'SET_CASE_ANALYSIS':
      return { ...state, caseAnalysis: action.payload }
    case 'SET_DOCUMENT':
      return { ...state, documents: { ...state.documents, [action.payload.key]: action.payload.content }, activeDocument: action.payload.key }
    case 'SET_ACTIVE_DOCUMENT':
      return { ...state, activeDocument: action.payload }
    case 'RESET':
      return { ...initialState }
    default:
      return state
  }
}

export const LegalProvider = ({ children }) => {
  const [state, dispatch] = useReducer(reducer, initialState)

  const sendMessage = useCallback(async (message) => {
    dispatch({ type: 'ADD_USER_MESSAGE', payload: message })
    dispatch({ type: 'SET_TYPING', payload: true })

    // Simulate AI response delay
    await new Promise((r) => setTimeout(r, 1200 + Math.random() * 800))

    const lowerMsg = message.toLowerCase()
    let response

    if (lowerMsg.includes('fir') || lowerMsg.includes('police') || lowerMsg.includes('crime')) {
      response = DEMO_CHAT_RESPONSES['fir']
    } else if (lowerMsg.includes('consumer') || lowerMsg.includes('defective') || lowerMsg.includes('refund') || lowerMsg.includes('product')) {
      response = DEMO_CHAT_RESPONSES['consumer']
    } else if (lowerMsg.includes('rti') || lowerMsg.includes('right to information') || lowerMsg.includes('government')) {
      response = DEMO_CHAT_RESPONSES['rti']
    } else if (lowerMsg.includes('rent') || lowerMsg.includes('landlord') || lowerMsg.includes('tenant') || lowerMsg.includes('lease')) {
      response = DEMO_CHAT_RESPONSES['rental']
    } else if (lowerMsg.includes('workplace') || lowerMsg.includes('harass') || lowerMsg.includes('employer') || lowerMsg.includes('salary') || lowerMsg.includes('fired')) {
      response = DEMO_CHAT_RESPONSES['workplace']
    } else {
      response = {
        answer: `I understand your concern. Based on what you've described, here are some general steps you can take:\n\n1. **Document everything** — Keep records of all relevant communications, transactions, and incidents.\n\n2. **Seek legal aid** — If you cannot afford a lawyer, you're entitled to free legal aid under the Legal Services Authorities Act, 1987. Contact your nearest District Legal Services Authority (DLSA).\n\n3. **Explore alternative dispute resolution** — Mediation and arbitration are often faster and cheaper than court proceedings.\n\n4. **File appropriate complaints** — Depending on your issue, you can approach:\n   - Police Station (criminal matters)\n   - Consumer Forum (consumer disputes)\n   - Labour Commissioner (employment issues)\n   - Human Rights Commission (rights violations)\n\nCould you provide more specific details about your situation? For example:\n- Is this related to a **consumer complaint**, **property dispute**, **workplace issue**, or **criminal matter**?\n- What specific outcome are you looking for?`,
        category: 'General Legal Guidance',
        confidence: 75,
        relatedSections: ['Legal Services Authorities Act, 1987', 'Article 39A of Constitution'],
      }
    }

    dispatch({
      type: 'ADD_AI_MESSAGE',
      payload: {
        content: response.answer,
        category: response.category,
        confidence: response.confidence,
        relatedSections: response.relatedSections,
      },
    })
  }, [])

  const loadCaseAnalysis = useCallback(async () => {
    await new Promise((r) => setTimeout(r, 1500))
    dispatch({ type: 'SET_CASE_ANALYSIS', payload: DEMO_CASE_ANALYSIS })
    return DEMO_CASE_ANALYSIS
  }, [])

  const generateDocument = useCallback(async (type) => {
    await new Promise((r) => setTimeout(r, 1000))
    const docMap = {
      legalNotice: { key: 'legalNotice', label: 'Legal Notice', content: DEMO_DOCUMENTS.legalNotice },
      rti: { key: 'rti', label: 'RTI Application', content: DEMO_DOCUMENTS.rtiApplication },
      complaint: { key: 'complaint', label: 'Consumer Complaint', content: DEMO_DOCUMENTS.complaint },
    }
    const doc = docMap[type] || docMap.legalNotice
    dispatch({ type: 'SET_DOCUMENT', payload: doc })
    return doc
  }, [])

  const reset = useCallback(() => dispatch({ type: 'RESET' }), [])

  const value = useMemo(
    () => ({
      ...state,
      sendMessage,
      loadCaseAnalysis,
      generateDocument,
      reset,
      demoDocuments: DEMO_DOCUMENTS,
      demoCaseAnalysis: DEMO_CASE_ANALYSIS,
    }),
    [state, sendMessage, loadCaseAnalysis, generateDocument, reset],
  )

  return <LegalContext.Provider value={value}>{children}</LegalContext.Provider>
}

export const useLegal = () => {
  const ctx = useContext(LegalContext)
  if (!ctx) throw new Error('useLegal must be used inside LegalProvider')
  return ctx
}
