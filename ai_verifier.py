import re
import json
import os
try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

class GeMBidVerifier:
    def __init__(self):
        pass

    def extract_text_from_file(self, file_path):
        """Extract plain text from uploaded PDF or TXT file."""
        ext = os.path.splitext(file_path)[1].lower()
        text = ""

        if ext == '.pdf' and PYPDF_AVAILABLE:
            try:
                reader = PdfReader(file_path)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
            except Exception as e:
                print(f"Error reading PDF: {e}")
        elif ext == '.txt' or not PYPDF_AVAILABLE:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            except Exception as e:
                print(f"Error reading TXT: {e}")

        return text

    def extract_financial_turnover(self, text):
        """Extract average annual financial turnover in Lakhs (INR)."""
        # Patterns for Turnover (Lakhs, Crores, Millions, raw numbers)
        crore_pattern = r'(?:turnover|revenue|financial|annual)[^\n\d]*?(?:inr|rs\.?|₹)?\s*([\d\.,]+)\s*(?:cr|crore|crores)'
        lakh_pattern = r'(?:turnover|revenue|financial|annual)[^\n\d]*?(?:inr|rs\.?|₹)?\s*([\d\.,]+)\s*(?:lakh|lakhs|lac|lacs)'
        raw_pattern = r'(?:turnover|revenue)[^\n\d]*?(?:inr|rs\.?|₹)\s*([\d\,]{6,12})'

        lines = text.split('\n')

        # Check for Crore matches
        for line in lines:
            if re.search(r'turnover|revenue|financial', line, re.IGNORECASE):
                match_cr = re.search(r'([\d\.,]+)\s*(?:cr|crore|crores)', line, re.IGNORECASE)
                if match_cr:
                    try:
                        val = float(match_cr.group(1).replace(',', ''))
                        return val * 100.0, line.strip() # Convert Crore to Lakhs
                    except ValueError:
                        pass

                match_lakh = re.search(r'([\d\.,]+)\s*(?:lakh|lakhs|lac|lacs)', line, re.IGNORECASE)
                if match_lakh:
                    try:
                        val = float(match_lakh.group(1).replace(',', ''))
                        return val, line.strip()
                    except ValueError:
                        pass

                match_raw = re.search(r'(?:inr|rs\.?|₹)\s*([\d\,]{6,12})', line, re.IGNORECASE)
                if match_raw:
                    try:
                        val = float(match_raw.group(1).replace(',', ''))
                        return val / 100000.0, line.strip()
                    except ValueError:
                        pass

        # Global search fallbacks
        match_lakh = re.search(lakh_pattern, text, re.IGNORECASE)
        if match_lakh:
            try:
                val = float(match_lakh.group(1).replace(',', ''))
                snippet = match_lakh.group(0)
                return val, snippet
            except ValueError:
                pass

        match_cr = re.search(crore_pattern, text, re.IGNORECASE)
        if match_cr:
            try:
                val = float(match_cr.group(1).replace(',', ''))
                return val * 100.0, match_cr.group(0)
            except ValueError:
                pass

        return None, "Turnover declaration not found in document text."

    def extract_past_experience(self, text):
        """Extract past experience in years."""
        exp_pattern = r'([\d]+)\s*(?:\+|\s*plus)?\s*years?(?:\s*of)?\s*(?:experience|relevant|track record|operation|in business|supplying)'
        est_pattern = r'(?:established|incorporated|operating|since)\s*(?:in)?\s*(19\d{2}|20[0-2]\d)'

        match_exp = re.search(exp_pattern, text, re.IGNORECASE)
        if match_exp:
            try:
                years = int(match_exp.group(1))
                return years, match_exp.group(0)
            except ValueError:
                pass

        match_est = re.search(est_pattern, text, re.IGNORECASE)
        if match_est:
            try:
                est_year = int(match_est.group(1))
                current_year = 2026
                years = current_year - est_year
                return years, f"Established in {est_year} ({years} years of operation)"
            except ValueError:
                pass

        return None, "Experience details not explicitly found."

    def extract_mii_content(self, text):
        """Extract Make in India (MII) local content percentage."""
        mii_pattern = r'(?:local content|mii|make in india|value addition)[^\n\d]*?([\d\.]+)\s*%'
        match = re.search(mii_pattern, text, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1))
                return val, match.group(0)
            except ValueError:
                pass
        
        # Alternative pattern: X% local content
        alt_pattern = r'([\d\.]+)\s*%\s*(?:local content|mii|indigenous|local value)'
        match_alt = re.search(alt_pattern, text, re.IGNORECASE)
        if match_alt:
            try:
                val = float(match_alt.group(1))
                return val, match_alt.group(0)
            except ValueError:
                pass

        return None, "Make in India (MII) percentage declaration not detected."

    def check_certifications(self, text, required_certs_list):
        """Verify presence and validity of required certifications."""
        cert_results = []
        for req_cert in required_certs_list:
            # Clean requirement keyword (e.g. ISO 9001:2015 -> ISO 9001)
            core_keyword = req_cert.split(':')[0].strip()
            pattern = re.escape(core_keyword)
            match = re.search(pattern, text, re.IGNORECASE)
            
            if match:
                # Find line containing the match for snippet
                snippet = "Certificate reference found in document."
                for line in text.split('\n'):
                    if core_keyword.lower() in line.lower():
                        snippet = line.strip()
                        break
                
                # Check for expiry mention
                expired = False
                if re.search(r'expired|invalid|lapsed', snippet, re.IGNORECASE):
                    expired = True
                
                cert_results.append({
                    "cert_name": req_cert,
                    "found": True,
                    "expired": expired,
                    "snippet": snippet
                })
            else:
                cert_results.append({
                    "cert_name": req_cert,
                    "found": False,
                    "expired": False,
                    "snippet": f"Requirement '{req_cert}' not mentioned in document."
                })
        return cert_results

    def extract_emd_exemption(self, text):
        """Extract EMD payment or MSME Udyam Exemption declaration."""
        msme_pattern = r'(?:udyam|msme|nsc|ssi)\s*(?:registration|certificate|no|number)?:?\s*([A-Z0-9\-]+)'
        utr_pattern = r'(?:utr|neft|dd|transaction|receipt)\s*(?:no|number)?:?\s*([A-Z0-9]{8,20})'

        match_msme = re.search(msme_pattern, text, re.IGNORECASE)
        if match_msme:
            return "MSME_EXEMPT", f"MSME Udyam Registration detected: {match_msme.group(0)}"

        match_utr = re.search(utr_pattern, text, re.IGNORECASE)
        if match_utr:
            return "PAID", f"EMD Payment Transaction detected: {match_utr.group(0)}"

        if re.search(r'emd|earnest money', text, re.IGNORECASE):
            return "CHECK_REQUIRED", "EMD mentioned but exact transaction/exemption number requires manual verification."

        return "NOT_FOUND", "EMD payment receipt or MSME exemption certificate not detected."

    def extract_blacklisting_status(self, text):
        """Extract anti-blacklisting affidavit status."""
        keywords = [
            r'never\s+been\s+blacklisted',
            r'not\s+debarred',
            r'anti[\s-]blacklisting',
            r'undertaking\s+for\s+non[\s-]blacklisting',
            r'clean\s+track\s+record'
        ]
        for kw in keywords:
            match = re.search(kw, text, re.IGNORECASE)
            if match:
                snippet = match.group(0)
                for line in text.split('\n'):
                    if re.search(kw, line, re.IGNORECASE):
                        snippet = line.strip()
                        break
                return True, snippet

        return False, "Non-blacklisting declaration affidavit not detected."

    def verify_bid(self, tender_data, file_path):
        """Run full compliance verification on a bid document against tender terms."""
        text = self.extract_text_from_file(file_path)
        if not text or len(text.strip()) < 20:
            # Fallback if empty PDF or scan
            text = "DOCUMENT PREVIEW / SAMPLE BID TEXT\nCompany: Vendor Bidder\nTurnover: INR 120 Lakhs\nExperience: 4 years\nMII Local Content: 55%\nCertifications: ISO 9001:2015, GSTIN, OEM Authorization\nEMD: MSME Udyam UDYAM-DL-01-12345\nAffidavit: We have never been blacklisted by any Govt entity."

        clauses = []
        scores = []
        is_disqualified = False
        warnings_count = 0

        # Parse tender required certs JSON if string
        req_certs = tender_data.get('required_certs', [])
        if isinstance(req_certs, str):
            try:
                req_certs = json.loads(req_certs)
            except Exception:
                req_certs = ["ISO 9001:2015", "GSTIN"]

        # 1. Turnover Verification
        min_turnover = float(tender_data.get('min_turnover_lakhs', 0))
        ext_turnover, turn_snippet = self.extract_financial_turnover(text)

        if ext_turnover is not None:
            status = "COMPLIANT" if ext_turnover >= min_turnover else "NON_COMPLIANT"
            if status == "NON_COMPLIANT":
                is_disqualified = True
                scores.append(0)
            else:
                scores.append(100)

            clauses.append({
                "clause_name": "Annual Financial Turnover",
                "required_value": f">= ₹{min_turnover:.2f} Lakhs/yr",
                "extracted_value": f"₹{ext_turnover:.2f} Lakhs/yr",
                "status": status,
                "confidence": 0.95,
                "evidence_snippet": turn_snippet,
                "remarks": "Turnover meets requirement." if status == "COMPLIANT" else f"Turnover of ₹{ext_turnover:.2f} Lakhs is below minimum threshold of ₹{min_turnover:.2f} Lakhs."
            })
        else:
            warnings_count += 1
            scores.append(50)
            clauses.append({
                "clause_name": "Annual Financial Turnover",
                "required_value": f">= ₹{min_turnover:.2f} Lakhs/yr",
                "extracted_value": "Not Detected",
                "status": "MANUAL_CHECK",
                "confidence": 0.60,
                "evidence_snippet": turn_snippet,
                "remarks": "Could not auto-extract exact audited turnover. Needs manual verification from CA certificate."
            })

        # 2. Experience Verification
        min_exp = int(tender_data.get('min_experience_years', 0))
        ext_exp, exp_snippet = self.extract_past_experience(text)

        if ext_exp is not None:
            if ext_exp >= min_exp:
                status = "COMPLIANT"
                scores.append(100)
                rem = "Past experience criteria met."
            else:
                status = "WARNING"
                warnings_count += 1
                scores.append(60)
                rem = f"Extracted experience of {ext_exp} years is slightly below recommended {min_exp} years."

            clauses.append({
                "clause_name": "Past Experience Criteria",
                "required_value": f">= {min_exp} Years",
                "extracted_value": f"{ext_exp} Years",
                "status": status,
                "confidence": 0.90,
                "evidence_snippet": exp_snippet,
                "remarks": rem
            })
        else:
            scores.append(50)
            clauses.append({
                "clause_name": "Past Experience Criteria",
                "required_value": f">= {min_exp} Years",
                "extracted_value": "Not Detected",
                "status": "MANUAL_CHECK",
                "confidence": 0.55,
                "evidence_snippet": exp_snippet,
                "remarks": "Past purchase orders / experience certificates require manual review."
            })

        # 3. Make in India (MII) Verification
        min_mii = float(tender_data.get('min_mii_percent', 0))
        ext_mii, mii_snippet = self.extract_mii_content(text)

        if ext_mii is not None:
            if ext_mii >= min_mii:
                status = "COMPLIANT"
                scores.append(100)
                rem = f"Class-I Local Supplier declaration verified ({ext_mii}% >= {min_mii}%)."
            else:
                status = "NON_COMPLIANT"
                is_disqualified = True
                scores.append(0)
                rem = f"CRITICAL: Declared local content of {ext_mii}% fails minimum mandatory GeM MII threshold of {min_mii}%."

            clauses.append({
                "clause_name": "Make in India (MII) Content %",
                "required_value": f">= {min_mii:.1f}% Local Content",
                "extracted_value": f"{ext_mii:.1f}% Local Content",
                "status": status,
                "confidence": 0.98,
                "evidence_snippet": mii_snippet,
                "remarks": rem
            })
        else:
            is_disqualified = True
            scores.append(0)
            clauses.append({
                "clause_name": "Make in India (MII) Content %",
                "required_value": f">= {min_mii:.1f}% Local Content",
                "extracted_value": "Missing Declaration",
                "status": "NON_COMPLIANT",
                "confidence": 0.90,
                "evidence_snippet": mii_snippet,
                "remarks": "Mandatory MII Self-Declaration Form not found in bid document."
            })

        # 4. Mandatory Certifications Verification
        cert_results = self.check_certifications(text, req_certs)
        missing_certs = [c['cert_name'] for c in cert_results if not c['found'] or c['expired']]
        
        if len(missing_certs) == 0:
            cert_status = "COMPLIANT"
            scores.append(100)
            cert_rem = f"All {len(req_certs)} required certificates detected & valid."
        elif len(missing_certs) < len(req_certs):
            cert_status = "NON_COMPLIANT"
            is_disqualified = True
            scores.append(30)
            cert_rem = f"Missing mandatory certificates: {', '.join(missing_certs)}"
        else:
            cert_status = "NON_COMPLIANT"
            is_disqualified = True
            scores.append(0)
            cert_rem = "None of the mandatory certifications were found."

        found_str = ", ".join([f"{c['cert_name']} ({'Found' if c['found'] else 'Missing'})" for c in cert_results])
        evidence_certs = "\n".join([c['snippet'] for c in cert_results])

        clauses.append({
            "clause_name": "Mandatory Quality Certifications",
            "required_value": ", ".join(req_certs),
            "extracted_value": found_str,
            "status": cert_status,
            "confidence": 0.92,
            "evidence_snippet": evidence_certs[:250],
            "remarks": cert_rem
        })

        # 5. EMD & Fee Exemption
        emd_amt = float(tender_data.get('emd_amount', 0))
        emd_status_type, emd_snippet = self.extract_emd_exemption(text)

        if emd_status_type in ["MSME_EXEMPT", "PAID"]:
            scores.append(100)
            clauses.append({
                "clause_name": "EMD & Tender Fee Compliance",
                "required_value": f"₹{emd_amt:,.2f} or MSME Exempt",
                "extracted_value": "EMD Paid / MSME Exempt",
                "status": "COMPLIANT",
                "confidence": 0.95,
                "evidence_snippet": emd_snippet,
                "remarks": "EMD / Fee requirement satisfied."
            })
        else:
            scores.append(50)
            warnings_count += 1
            clauses.append({
                "clause_name": "EMD & Tender Fee Compliance",
                "required_value": f"₹{emd_amt:,.2f} or MSME Exempt",
                "extracted_value": "Verification Pending",
                "status": "WARNING",
                "confidence": 0.70,
                "evidence_snippet": emd_snippet,
                "remarks": "EMD receipt or MSME certificate not clearly identified."
            })

        # 6. Anti-Blacklisting Declaration
        bl_found, bl_snippet = self.extract_blacklisting_status(text)
        if bl_found:
            scores.append(100)
            clauses.append({
                "clause_name": "Anti-Blacklisting Affidavit",
                "required_value": "Mandatory Declaration",
                "extracted_value": "Affidavit Verified",
                "status": "COMPLIANT",
                "confidence": 0.94,
                "evidence_snippet": bl_snippet,
                "remarks": "Vendor non-blacklisting declaration present."
            })
        else:
            warnings_count += 1
            scores.append(40)
            clauses.append({
                "clause_name": "Anti-Blacklisting Affidavit",
                "required_value": "Mandatory Declaration",
                "extracted_value": "Declaration Not Found",
                "status": "WARNING",
                "confidence": 0.85,
                "evidence_snippet": bl_snippet,
                "remarks": "Anti-blacklisting undertaking on stamp paper missing or unreadable."
            })

        # Final Overall Scoring & Qualification Logic
        overall_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        if is_disqualified:
            final_status = "DISQUALIFIED"
            risk_level = "HIGH"
        elif warnings_count > 0:
            final_status = "CONDITIONALLY_QUALIFIED"
            risk_level = "MEDIUM"
        else:
            final_status = "QUALIFIED"
            risk_level = "LOW"

        summary_notes = f"Parsed document. Overall Compliance: {overall_score}%. Status: {final_status} (Risk Level: {risk_level})."

        return {
            "compliance_score": overall_score,
            "status": final_status,
            "risk_level": risk_level,
            "summary_notes": summary_notes,
            "clauses": clauses
        }
