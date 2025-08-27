# 🎭 Reddit Mode - Anonymous Contact Display
## Design Document for Bias-Free Candidate Evaluation

---

## 🎯 **Overview**

Reddit Mode is an optional feature that anonymizes contact information during job matching to eliminate unconscious bias based on gender, race, age, or other demographic factors. Candidates are evaluated purely on their skills, experience, and qualifications.

---

## 🏗️ **Core Features**

### 1. **Anonymous Contact Display**
- **Pseudonym Generation**: Each contact gets a unique anonymous ID (e.g., "Senior_Engineer_42", "Sales_Pro_ABC123")
- **Masked Information**: Names, emails, and LinkedIn URLs are hidden
- **Preserved Data**: Skills, experience, company, and role information remain visible
- **Reversible**: Full contact details are revealed after candidate selection

### 2. **Configurable Privacy Levels**
```json
{
  "hide_names": true,
  "hide_companies": false,
  "hide_emails": true,
  "hide_linkedin_urls": true,
  "generate_pseudonyms": true,
  "show_company_industry": true,
  "show_position_level": true
}
```

### 3. **Organization-Level Settings**
- Enable/disable Reddit Mode per organization
- Set default anonymous display preferences
- Override settings per job posting

---

## 🔧 **Technical Implementation**

### Database Schema Updates

#### Contacts Table
```sql
-- Anonymous mode data
anonymous_id VARCHAR(50) UNIQUE, -- e.g., "RedditUser_ABC123"
anonymous_name VARCHAR(255), -- e.g., "Senior_Engineer_42"
is_anonymous BOOLEAN DEFAULT false,
```

#### Job Descriptions Table
```sql
-- Anonymous mode settings
use_anonymous_mode BOOLEAN DEFAULT false,
anonymous_display_settings JSONB,
```

#### Organizations Table
```sql
-- Anonymous mode settings
enable_anonymous_mode BOOLEAN DEFAULT false,
default_anonymous_settings JSONB,
```

### Pseudonym Generation Algorithm

```python
class AnonymousContactManager:
    def generate_pseudonym(self, contact_data):
        """
        Generate anonymous pseudonym based on contact data
        """
        # Extract role and seniority
        role = contact_data.get('role_tag', 'Professional')
        seniority = contact_data.get('seniority_tag', 'Mid')
        
        # Generate random suffix
        suffix = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))
        
        # Create pseudonym
        pseudonym = f"{seniority}_{role}_{suffix}"
        
        return pseudonym
    
    def anonymize_contact(self, contact_data, settings):
        """
        Anonymize contact data based on settings
        """
        anonymized = contact_data.copy()
        
        if settings.get('hide_names', True):
            anonymized['first_name'] = 'Anonymous'
            anonymized['last_name'] = ''
        
        if settings.get('hide_emails', True):
            anonymized['email'] = 'hidden@example.com'
        
        if settings.get('hide_linkedin_urls', True):
            anonymized['linkedin_url'] = ''
        
        if settings.get('generate_pseudonyms', True):
            anonymized['anonymous_name'] = self.generate_pseudonym(contact_data)
        
        return anonymized
```

---

## 🎨 **User Interface Design**

### 1. **Job Creation Interface**
```
┌─────────────────────────────────────────────────────────┐
│ 🎭 Reddit Mode Settings                                 │
│                                                         │
│ ☑️ Enable anonymous candidate display                  │
│                                                         │
│ Privacy Settings:                                       │
│ ☑️ Hide candidate names                                │
│ ☑️ Hide email addresses                                │
│ ☑️ Hide LinkedIn URLs                                  │
│ ☐ Hide company names                                   │
│ ☑️ Generate pseudonyms                                 │
│ ☑️ Show company industry tags                          │
│                                                         │
│ ℹ️  Candidates will be displayed with pseudonyms       │
│    to eliminate unconscious bias during evaluation.    │
└─────────────────────────────────────────────────────────┘
```

### 2. **Anonymous Candidate Display**
```
┌─────────────────────────────────────────────────────────┐
│ 🎭 Anonymous Candidates                                │
│                                                         │
│ #1: Senior_Engineer_ABC123                             │
│ Position: Senior Software Engineer                     │
│ Company: [Tech Company]                                │
│ Industry: SaaS, B2B                                    │
│ Skills: Python, React, AWS, Docker                     │
│ Platforms: GitHub, Jira, Slack                         │
│ Match Score: 92.5                                      │
│                                                         │
│ #2: Sales_Pro_DEF456                                   │
│ Position: Account Executive                            │
│ Company: [Sales Company]                               │
│ Industry: CRM, Enterprise                              │
│ Skills: Sales, Negotiation, CRM, Prospecting           │
│ Platforms: Salesforce, HubSpot, LinkedIn               │
│ Match Score: 89.2                                      │
│                                                         │
│ [Select Candidates] [Reveal Identities]                │
└─────────────────────────────────────────────────────────┘
```

### 3. **Identity Revelation**
```
┌─────────────────────────────────────────────────────────┐
│ 🔓 Reveal Candidate Identities                         │
│                                                         │
│ ⚠️  This action will permanently reveal the names      │
│     and contact information of selected candidates.    │
│                                                         │
│ Selected Candidates:                                   │
│ • Senior_Engineer_ABC123 → John Smith                  │
│ • Sales_Pro_DEF456 → Sarah Johnson                     │
│                                                         │
│ [Confirm & Send Referral Request] [Cancel]             │
└─────────────────────────────────────────────────────────┘
```

---

## 🔒 **Privacy & Security**

### 1. **Data Protection**
- Anonymous IDs are cryptographically secure
- No correlation between pseudonyms and real identities in logs
- Audit trail for identity revelation events
- GDPR compliance for data anonymization

### 2. **Access Control**
- Only authorized users can reveal identities
- Time-limited access to anonymous data
- Audit logging for all anonymous mode actions

### 3. **Data Retention**
- Anonymous data is automatically cleaned up after job posting closes
- Pseudonyms are regenerated for each job posting
- No permanent storage of anonymous-to-real mappings

---

## 📊 **Analytics & Insights**

### 1. **Bias Reduction Metrics**
- Comparison of candidate selection rates with/without anonymous mode
- Diversity metrics in selected candidates
- Time spent evaluating candidates (anonymous vs. identified)

### 2. **Feature Usage Analytics**
- Organizations using Reddit Mode
- Most common privacy settings
- User feedback and satisfaction scores

### 3. **Performance Impact**
- Processing time for pseudonym generation
- Database query performance with anonymous data
- Memory usage for anonymization processes

---

## 🚀 **Implementation Roadmap**

### Phase 1: Core Infrastructure (Week 1-2)
- [ ] Database schema updates
- [ ] Pseudonym generation algorithm
- [ ] Basic anonymization functions
- [ ] API endpoints for anonymous data

### Phase 2: User Interface (Week 3-4)
- [ ] Job creation interface with Reddit Mode toggle
- [ ] Anonymous candidate display
- [ ] Identity revelation workflow
- [ ] Settings management interface

### Phase 3: Advanced Features (Week 5-6)
- [ ] Configurable privacy levels
- [ ] Organization-level settings
- [ ] Audit logging and analytics
- [ ] Performance optimization

### Phase 4: Testing & Launch (Week 7-8)
- [ ] User acceptance testing
- [ ] Bias reduction validation
- [ ] Performance testing
- [ ] Documentation and training

---

## 🎯 **Success Metrics**

### 1. **Bias Reduction**
- Increase in diversity of selected candidates
- More balanced gender representation
- Reduced correlation between candidate selection and demographic factors

### 2. **User Adoption**
- 30% of organizations enable Reddit Mode within 3 months
- 80% user satisfaction score
- Positive feedback from HR professionals

### 3. **Technical Performance**
- < 100ms additional processing time for anonymization
- Zero data leaks or privacy breaches
- 99.9% uptime for anonymous mode features

---

## 🔮 **Future Enhancements**

### 1. **Advanced Anonymization**
- AI-powered pseudonym generation based on personality traits
- Dynamic privacy levels based on job requirements
- Voice and video anonymization for interviews

### 2. **Bias Detection**
- Machine learning models to detect unconscious bias patterns
- Real-time bias alerts during candidate evaluation
- Bias reduction recommendations

### 3. **Integration Features**
- Anonymous mode for external job boards
- API access for third-party HR tools
- Mobile app support for anonymous candidate review

---

## 💡 **Best Practices**

### 1. **For Organizations**
- Enable Reddit Mode for all senior-level positions
- Train hiring managers on bias-free evaluation
- Regularly review diversity metrics
- Gather feedback from candidates on the process

### 2. **For Users**
- Focus on skills and experience during anonymous evaluation
- Use structured evaluation criteria
- Document decision-making process
- Provide feedback on the anonymous mode experience

### 3. **For Developers**
- Ensure secure pseudonym generation
- Implement comprehensive audit logging
- Test with diverse datasets
- Monitor for potential bias in the anonymization algorithm

---

## 🎭 **Conclusion**

Reddit Mode represents a significant step forward in creating fair, unbiased hiring processes. By anonymizing candidate information during the initial evaluation phase, organizations can focus purely on qualifications and skills, leading to more diverse and inclusive hiring outcomes.

The feature is designed to be:
- **Optional**: Organizations can choose to enable it
- **Configurable**: Privacy levels can be adjusted
- **Secure**: Robust data protection measures
- **Transparent**: Clear audit trails and user control
- **Effective**: Measurable bias reduction outcomes

This implementation will help organizations build more diverse teams while maintaining the efficiency and effectiveness of their referral-based hiring processes.



