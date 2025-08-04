# 🎓 Vocabulary Training System Tutorial

## Overview
The Custom Vocabulary Training System allows CitrixTranscriber to learn and automatically correct medical terminology and other specialized vocabulary that speech recognition often gets wrong.

## 🚀 How to Access Vocabulary Settings

1. **Open Settings**: In CitrixTranscriber, go to the Settings window
2. **Find Vocabulary Tab**: Click on "Vocabulary" in the left sidebar
3. **You'll see three main sections**:
   - **Add New Term** (light gray box)
   - **Import Template** (light blue box)
   - **Current Vocabulary** (main area)

## 📝 Adding Custom Terms

### Method 1: Manual Entry
1. **In the "Add New Term" section:**
   - **Correct Term**: Enter the proper spelling (e.g., "azithromycin")
   - **Common Mistakes**: Enter what the system usually transcribes wrong, separated by commas (e.g., "as throw my sin, azthr my sin")
   - **Category**: Choose the appropriate category:
     - `General` - General terms
     - `Medication` - Drug names
     - `Medical Terms` - Conditions, procedures
     - `Names` - Doctor names, places
2. **Click "Add Term"**
3. **Success!** The term is now saved and will automatically correct in future transcriptions

### Method 2: Template Import
1. **In the "Import Template" section:**
   - **Select template**: Choose "General Medicine" (more templates coming soon)
   - **Click "Import Template"**
   - **Result**: 10+ common medical terms are automatically added

## 🔧 How the System Works

### Automatic Corrections
Once you've added vocabulary terms, the system automatically corrects transcriptions:

**Example:**
- You dictate: *"Patient needs as throw my sin 500mg daily"*
- System corrects to: *"Patient needs azithromycin 500mg daily"*
- **You see the correction happen instantly!**

### Learning from Corrections
The system also learns from your manual corrections:

1. **First correction**: System remembers the mistake
2. **Second correction**: System promotes it to permanent vocabulary
3. **Future transcriptions**: Automatically corrected

## 📊 Managing Your Vocabulary

### Viewing Current Terms
- **Stats Box**: Shows total terms, usage, and categories
- **Vocabulary List**: Shows all your custom terms with:
  - **Bold term**: The correct spelling
  - **Category**: (medication), (medical_terms), etc.
  - **Variations**: What mistakes it corrects
  - **Usage count**: How often it's been used

### Search and Filter
- **Search box**: Type to find specific terms
- **Real-time filtering**: List updates as you type

### Deleting Terms
- **Delete button**: Red button next to each term
- **Confirmation**: System asks before deleting
- **Instant update**: List refreshes immediately

## 🎯 Best Practices

### 1. Start with Common Mistakes
Add terms you know the system gets wrong frequently:
```
Correct: pneumothorax
Mistakes: new motor ax, pneumo thorax, new mo thorax
```

### 2. Use Templates
Import the General Medicine template first, then add your specialty terms.

### 3. Categories Matter
Choose the right category - it helps with organization and future features.

### 4. Include Variations
Think about different ways the system might mishear the term:
```
Correct: acetaminophen  
Mistakes: a seat a min o fen, acetyl amino phen, a c t amino phen
```

## 🔄 Real-World Workflow

### Scenario: Adding a New Medication
1. **You dictate**: *"Prescribe bye prof in 400mg"*
2. **System transcribes**: *"Prescribe bye prof in 400mg"* (wrong)
3. **You notice the error**: Should be "ibuprofen"
4. **Add to vocabulary**:
   - Correct Term: `ibuprofen`
   - Mistakes: `bye prof in, eye bu prof in`
   - Category: `Medication`
5. **Next time**: System automatically corrects it!

### Scenario: Importing for New Specialty
1. **Starting cardiology practice**: Import General Medicine template
2. **Add cardiology-specific terms**:
   - `electrocardiogram` → `electro cardio gram, ECG, EKG`
   - `echocardiogram` → `echo cardio gram, echo gram`
   - `myocardial infarction` → `my cardial infraction`
3. **Result**: Dramatically improved accuracy for cardiology dictation

## 📈 Monitoring Performance

### Statistics to Watch
- **Total terms**: How many custom terms you have
- **Total usage**: How often corrections are applied
- **Categories**: Distribution of your vocabulary

### Success Indicators
- **Increasing usage counts**: Shows the system is working
- **Fewer manual corrections needed**: Vocabulary is comprehensive
- **Better transcription accuracy**: Overall improvement

## 🛠️ Troubleshooting

### Problem: Term not correcting
**Solution**: Check if the variation exactly matches what's transcribed
- Look at the exact transcription text
- Add the exact mistake to variations

### Problem: Wrong corrections
**Solution**: Delete the problematic term and re-add with correct variations

### Problem: Not seeing vocabulary tab
**Solution**: Make sure you're using the latest version with vocabulary support

## 💡 Advanced Tips

### 1. Case Sensitivity
The system preserves your original capitalization:
- `AZITHROMYCIN` stays uppercase
- `azithromycin` stays lowercase  
- `Azithromycin` stays title case

### 2. Whole Word Matching
The system only corrects complete words, not partial matches, preventing unwanted corrections.

### 3. Export/Import (Coming Soon)
You'll be able to share vocabulary files with colleagues or backup your custom terms.

## 🎉 Getting Started Checklist

- [ ] Open Settings → Vocabulary tab
- [ ] Import "General Medicine" template
- [ ] Add 3-5 terms you know get transcribed wrong
- [ ] Do a test dictation with those terms
- [ ] Verify corrections are working
- [ ] Add more terms as needed

**You're now ready to dramatically improve your transcription accuracy!** 

The vocabulary system learns and adapts to your specific terminology, making CitrixTranscriber increasingly accurate over time. 