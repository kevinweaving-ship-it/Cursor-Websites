# README: app.sas_id_personal

## **MASTER SAILOR DATABASE**

This is the **central repository** for all sailor information in the SA Sailing system. It contains comprehensive personal, sailing, and administrative data for 27,726+ sailors.

---

## **TABLE OVERVIEW**

| Property | Value |
|----------|-------|
| **Schema** | `app` |
| **Table Name** | `sas_id_personal` |
| **Primary Key** | `id` (integer, NOT NULL) |
| **Unique Key** | `sa_sailing_id` (character varying, NOT NULL) |
| **Row Count** | ~27,726 sailors |
| **Table Size** | ~10 MB |
| **Purpose** | Master database for all sailor information |

---

## **CORE IDENTITY COLUMNS**

### **Primary Identifiers**
- **`id`** (integer, NOT NULL) - Internal database ID
- **`sa_sailing_id`** (character varying, NOT NULL) - Official SA Sailing ID (e.g., "00001", "12345")
- **`first_name`** (character varying) - Sailor's first name
- **`last_name`** (character varying) - Sailor's last name  
- **`full_name`** (character varying) - Complete name (computed/concatenated)

### **Personal Information**
- **`second_name`** (character varying) - Middle/second name
- **`year_of_birth`** (integer) - Birth year
- **`date_of_birth`** (date) - Full birth date
- **`age`** (integer) - Current age (computed)
- **`gender`** (character varying) - M/F/Other
- **`nationality`** (character varying) - Default: 'South African'

---

## **LOCATION & CLUB MEMBERSHIP**

### **Club Memberships** (Multi-club support)
- **`club_1`** (character varying) - Primary club code
- **`club_2`** (character varying) - Secondary club code
- **`club_3`** (character varying) - Third club code
- **`club_4`** (character varying) - Fourth club code
- **`club_5`** (character varying) - Fifth club code
- **`primary_club`** (character varying) - Main club affiliation

### **Club Join Dates & Status**
- **`club_1_join_date`** (date) - When joined club_1
- **`club_2_join_date`** (date) - When joined club_2
- **`club_3_join_date`** (date) - When joined club_3
- **`club_4_join_date`** (date) - When joined club_4
- **`club_5_join_date`** (date) - When joined club_5
- **`club_1_member_status`** (character varying) - Active/Inactive/etc
- **`club_2_member_status`** (character varying) - Active/Inactive/etc
- **`club_3_member_status`** (character varying) - Active/Inactive/etc
- **`club_4_member_status`** (character varying) - Active/Inactive/etc
- **`club_5_member_status`** (character varying) - Active/Inactive/etc

### **Geographic Location**
- **`province`** (character varying) - Province code (WC, GP, KZN, etc.)
- **`city`** (character varying) - City name
- **`country`** (character varying) - Default: 'South Africa'

---

## **SAILING INFORMATION**

### **Primary Sailing Details**
- **`primary_class`** (character varying) - Main boat class (420, ILCA 6, etc.)
- **`primary_sailno`** (character varying) - Primary sail number

### **Regatta History Tracking**
- **`first_regatta_no`** (integer) - First regatta participated in
- **`last_regatta_no`** (integer) - Most recent regatta
- **`regatta_1`** through **`regatta_500`** (text) - Individual regatta records

---

## **COMMUNICATION & CONTACT**

### **Contact Information**
- **`email`** (character varying) - Primary email address
- **`phone_primary`** (character varying) - Main phone number
- **`phone_secondary`** (character varying) - Secondary phone number
- **`address_line1`** (character varying) - Street address
- **`address_line2`** (character varying) - Additional address info
- **`postal_code`** (character varying) - Postal/ZIP code

### **Communication Preferences**
- **`preferred_language`** (character varying) - Default: 'English'
- **`communication_preferences_1`** (character varying) - Contact method 1
- **`communication_preferences_2`** (character varying) - Contact method 2
- **`communication_preferences_3`** (character varying) - Contact method 3
- **`communication_preferences_4`** (character varying) - Contact method 4

### **Social Media**
- **`social_media_handles`** (jsonb) - Social media accounts (JSON format)

---

## **QUALIFICATIONS & ROLES**

### **SA Sailing Certifications**
- **`sa_sailing_certifications_roles`** (character varying) - Official certifications
- **`sa_sailing_return_to_play`** (character varying) - Return to play status

### **Instruction & Coaching**
- **`senior_instructor`** (character varying) - Senior instructor status
- **`instructor_keelboat`** (character varying) - Keelboat instructor
- **`instructor_dinghy_multihull`** (character varying) - Dinghy/multihull instructor
- **`assistant_instructor`** (character varying) - Assistant instructor
- **`senior_race_coach`** (character varying) - Senior race coach
- **`race_coach_developer`** (character varying) - Race coach developer
- **`race_coach`** (character varying) - Race coach
- **`assistant_race_coach`** (character varying) - Assistant race coach

### **Judging & Race Management**
- **`judge_international_level_ij`** (character varying) - International judge
- **`judge_national_level`** (character varying) - National judge
- **`judge_regional_level`** (character varying) - Regional judge
- **`judge_club_level`** (character varying) - Club judge
- **`judge_district_level`** (character varying) - District judge
- **`race_officer_international_level`** (character varying) - International race officer
- **`race_officer_national_level`** (character varying) - National race officer
- **`race_officer_regional_level`** (character varying) - Regional race officer
- **`race_officer_club_level`** (character varying) - Club race officer
- **`race_officer_assistant`** (character varying) - Assistant race officer
- **`race_officer_facilitator`** (character varying) - Race officer facilitator

### **Safety & Technical**
- **`national_senior_safety_officer`** (character varying) - Senior safety officer
- **`sa_sailing_vessel_safety_officers`** (character varying) - Vessel safety officer
- **`sa_sailing_safety_boat_instructor`** (character varying) - Safety boat instructor
- **`safety_boat_operator`** (character varying) - Safety boat operator
- **`measurer`** (character varying) - Official measurer
- **`protest_committee`** (character varying) - Protest committee member
- **`technical_committee`** (character varying) - Technical committee member

### **Examiners & Surveyors**
- **`national_senior_examiner`** (character varying) - Senior examiner
- **`appointed_examiners`** (character varying) - Appointed examiner
- **`samsa_vessel_surveyors`** (character varying) - SAMSA vessel surveyor

### **Umpiring**
- **`umpire_national`** (character varying) - National umpire

---

## **CLUB ADMINISTRATIVE ROLES**

### **Club Leadership**
- **`commodore`** (character varying) - Club commodore
- **`vice_commodore`** (character varying) - Vice commodore
- **`committee_member`** (character varying) - Committee member
- **`club_secretary`** (character varying) - Club secretary
- **`club_treasurer`** (character varying) - Club treasurer
- **`club_chairman`** (character varying) - Club chairman
- **`club_director`** (character varying) - Club director
- **`club_manager`** (character varying) - Club manager
- **`member`** (character varying) - General member

### **Class Representatives**
- **`class_representative`** (character varying) - Class rep role

---

## **COACHING RELATIONSHIPS**

### **Coach Associations**
- **`coach_1_sas_id`** (integer) - Primary coach SAS ID
- **`coach_2_sas_id`** (integer) - Secondary coach SAS ID
- **`coach_3_sas_id`** (integer) - Third coach SAS ID
- **`coach_4_sas_id`** (integer) - Fourth coach SAS ID
- **`coach_5_sas_id`** (integer) - Fifth coach SAS ID

### **Parent/Guardian**
- **`parent_guardian_id`** (integer) - Parent/guardian SAS ID

---

## **SYSTEM MANAGEMENT**

### **Audit Trail**
- **`created_at`** (timestamp) - Record creation time
- **`updated_at`** (timestamp) - Last modification time
- **`created_by`** (character varying) - Who created the record

### **Additional Data**
- **`notes`** (text) - General notes
- **`personal_information`** (text) - Additional personal info
- **`profile_photo_path`** (character varying) - Photo file path
- **`sponsor_name_1`** through **`sponsor_name_5`** (character varying) - Sponsor information

### **Reserve Fields**
- **`reserve_215`** through **`reserve_250`** (text) - Future expansion fields
- **`placeholder_1`** through **`placeholder_9`** (character varying) - Temporary fields
- **`placeholder_1_qual`** through **`placeholder_6_qual`** (character varying) - Qualification placeholders
- **`placeholder_1_club`** through **`placeholder_9_club`** (character varying) - Club placeholders

---

## **KEY RELATIONSHIPS**

### **References Other Tables:**
- **`club_1` through `club_5`** → `app.clubs.club_code`
- **`primary_class`** → `app.class_id.class_name`
- **`province`** → `app.provinces.province_code`
- **`coach_X_sas_id`** → `app.sas_id_personal.id` (self-reference)
- **`parent_guardian_id`** → `app.sas_id_personal.id` (self-reference)

### **Referenced By:**
- **`app.regatta_XXX_results.helm_sas_id`** → `id`
- **`app.regatta_XXX_results.crew_sas_id`** → `id`

---

## **USAGE RULES**

### **Data Entry Rules:**
1. **`sa_sailing_id`** must be unique across all sailors
2. **`id`** is auto-generated, never manually set
3. **`primary_club`** should match one of `club_1` through `club_5`
4. **`full_name`** should be `first_name + ' ' + last_name`
5. **`age`** should be calculated from `date_of_birth`

### **Validation Rules:**
1. **Club codes** must exist in `app.clubs` table
2. **Province codes** must exist in `app.provinces` table
3. **Class names** must exist in `app.class_id` table
4. **Coach SAS IDs** must reference valid sailors in this table

### **Search & Lookup:**
- **Primary lookup**: `sa_sailing_id` (user-facing)
- **Internal lookup**: `id` (database joins)
- **Name search**: `first_name`, `last_name`, `full_name`
- **Club search**: `primary_club`, `club_1` through `club_5`

---

## **DATA SOURCE & SCRAPE ARCHITECTURE**

Scrape and registry expansion follow the corrected architecture: **registry expansion only**, no automatic merge into this table. See [SAS_SCRAPE_ARCHITECTURE.md](SAS_SCRAPE_ARCHITECTURE.md) for DOCUMENTED_SAS_MAX_ID vs DETECTED_SAS_MAX_ID, incremental scrape strategy, batch logging (`sas_scrape_batches`), and the rule that scraped results must not be written directly into race_results (staging only).

---

## **MAINTENANCE NOTES**

### **Regular Tasks:**
1. **Age updates**: Recalculate `age` from `date_of_birth`
2. **Club validation**: Ensure club codes exist in clubs table
3. **Duplicate checking**: Verify `sa_sailing_id` uniqueness
4. **Data cleanup**: Remove/update invalid references

### **Backup Priority:**
- **HIGHEST** - This is the master sailor database
- **Daily backups** recommended
- **Point-in-time recovery** capability essential

---

## **SECURITY CONSIDERATIONS**

### **Sensitive Data:**
- **Personal information**: Names, addresses, phone numbers
- **Birth dates**: Age verification data
- **Contact details**: Email, phone numbers
- **Medical information**: Return to play status

### **Access Control:**
- **Read access**: Limited to authorized personnel
- **Write access**: Restricted to data administrators
- **Delete access**: Super admin only
- **GDPR compliance**: Data retention and deletion policies required

---

*Last Updated: October 2024*
*Table Size: ~10 MB*
*Record Count: ~27,726 sailors*


