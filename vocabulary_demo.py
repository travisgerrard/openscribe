#!/usr/bin/env python3
"""
Vocabulary Training System Demo
Demonstrates the key features of the custom vocabulary system for CitrixTranscriber
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vocabulary.vocabulary_manager import get_vocabulary_manager
from vocabulary.vocabulary_api import handle_vocabulary_command


def demo_basic_functionality():
    """Demonstrate basic vocabulary functionality."""
    print("🔤 VOCABULARY TRAINING SYSTEM DEMO")
    print("=" * 50)
    
    # Get the vocabulary manager
    vocab_manager = get_vocabulary_manager()
    
    print("\n📝 1. ADDING CUSTOM TERMS")
    print("-" * 30)
    
    # Add some technical terms that Whisper often gets wrong
    technical_terms = [
        ("azithromycin", ["as throw my sin", "azthr my sin", "azith ro mycin"], "medication"),
        ("pneumothorax", ["new motor ax", "pneumo thorax", "new mo thorax"], "technical_terms"),
        ("acetaminophen", ["a seat a min o fen", "acetyl amino phen"], "medication"),
        ("Dr. Johnson", ["doctor johnson", "dr johnson"], "names")
    ]
    
    for correct, variations, category in technical_terms:
        vocab_manager.add_custom_term(correct, variations, category)
        print(f"✅ Added '{correct}' ({category}) with {len(variations)} variations")
    
    print(f"\n📊 Total vocabulary terms: {len(vocab_manager.custom_terms)}")
    
    print("\n🔧 2. APPLYING CORRECTIONS")
    print("-" * 30)
    
    # Test sentences with common transcription errors
    test_sentences = [
        "Person needs as throw my sin 500mg twice daily",
        "X-ray shows new motor ax in left lung",
        "Give a seat a min o fen for pain",
        "Consult with doctor johnson about the case"
    ]
    
    for original in test_sentences:
        corrected, corrections = vocab_manager.apply_corrections(original)
        print(f"Original: {original}")
        print(f"Corrected: {corrected}")
        if corrections:
            print(f"Applied {len(corrections)} corrections:")
            for corr in corrections:
                print(f"  • '{corr['original']}' → '{corr['corrected']}' ({corr['category']})")
        print()
    
    print("\n🧠 3. LEARNING FROM CORRECTIONS")
    print("-" * 30)
    
    # Simulate user corrections
    corrections_to_learn = [
        ("bye prof in", "ibuprofen", "pain medication"),
        ("electro cardio gram", "electrocardiogram", "diagnostic test"),
        ("bye prof in", "ibuprofen", "another case")  # Same correction again
    ]
    
    for original, corrected, context in corrections_to_learn:
        learned = vocab_manager.learn_from_correction(original, corrected, context)
        if learned:
            print(f"📚 Learned: '{original}' → '{corrected}'")
    
    print(f"\n🧠 Learning patterns: {len(vocab_manager.learning_patterns)}")
    print(f"📈 After learning, total terms: {len(vocab_manager.custom_terms)}")
    
    print("\n💡 4. SMART SUGGESTIONS")
    print("-" * 30)
    
    # Test suggestions for partial words
    test_words = ["azithro", "pneumo", "acetamin", "doctor"]
    
    for word in test_words:
        suggestions = vocab_manager.suggest_corrections(word)
        if suggestions:
            print(f"'{word}' → suggestions:")
            for sug in suggestions[:3]:  # Top 3 suggestions
                confidence = int(sug['confidence'] * 100)
                print(f"  • {sug['suggested']} ({confidence}% confidence, {sug['usage_count']} uses)")
        else:
            print(f"'{word}' → no suggestions")
    
    print("\n📊 5. VOCABULARY STATISTICS")
    print("-" * 30)
    
    stats = vocab_manager.get_vocabulary_stats()
    print(f"Total terms: {stats['total_terms']}")
    print(f"Total corrections learned: {stats['total_corrections']}")
    print(f"Total usage: {stats['total_usage']}")
    print("Categories:")
    for category, count in stats['categories'].items():
        print(f"  • {category}: {count} terms")


def demo_api_functionality():
    """Demonstrate the API functionality."""
    print("\n\n🌐 API FUNCTIONALITY DEMO")
    print("=" * 50)
    
    # Test API commands
    print("\n📝 Adding term via API:")
    result = handle_vocabulary_command(
        "add_term",
        correct_term="metformin",
        variations=["met form in", "met for min"],
        category="medication"
    )
    print(f"Result: {result}")
    
    print("\n📋 Getting vocabulary list:")
    result = handle_vocabulary_command("get_list")
    if result['success']:
        print(f"Found {len(result['terms'])} terms")
        for term in result['terms'][:3]:  # Show first 3
            print(f"  • {term['correct']} ({term['category']}) - used {term['usage_count']} times")
    
    print("\n📊 Getting stats:")
    result = handle_vocabulary_command("get_stats")
    if result['success']:
        stats = result['stats']
        print(f"Total terms: {stats['total_terms']}")
        print(f"Categories: {', '.join(stats['categories'].keys())}")


def demo_template_functionality():
    """Demonstrate template import functionality."""
    print("\n\n📋 TEMPLATE FUNCTIONALITY DEMO")
    print("=" * 50)
    
    # Test importing the general medicine template
    print("\n📥 Importing general medicine template:")
    result = handle_vocabulary_command(
        "import_template",
        template_name="general_medicine"
    )
    print(f"Import result: {result}")
    
    if result['success']:
        # Show stats after import
        stats_result = handle_vocabulary_command("get_stats")
        if stats_result['success']:
            stats = stats_result['stats']
            print(f"After import - Total terms: {stats['total_terms']}")


def main():
    """Run the complete demo."""
    try:
        demo_basic_functionality()
        demo_api_functionality()
        demo_template_functionality()
        
        print("\n\n🎉 DEMO COMPLETE!")
        print("=" * 50)
        print("Key Features Demonstrated:")
        print("✅ Custom term management")
        print("✅ Automatic text correction")
        print("✅ Learning from user corrections")  
        print("✅ Smart suggestions")
        print("✅ Template importing")
        print("✅ API integration")
        print("✅ Category organization")
        print("✅ Usage statistics")
        
        print("\nThe vocabulary system is ready for integration with CitrixTranscriber!")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 