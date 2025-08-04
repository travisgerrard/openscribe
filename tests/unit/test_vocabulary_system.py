"""
Test suite for the vocabulary training system
"""

import unittest
import tempfile
import shutil
import os
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from vocabulary.vocabulary_manager import VocabularyManager
from vocabulary.vocabulary_api import VocabularyAPI, handle_vocabulary_command


class TestVocabularyManager(unittest.TestCase):
    """Test the core vocabulary manager functionality."""
    
    def setUp(self):
        """Set up test environment with temporary directory."""
        self.test_dir = tempfile.mkdtemp()
        self.vocab_manager = VocabularyManager(config_dir=self.test_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
    
    def test_add_custom_term(self):
        """Test adding custom terms."""
        self.vocab_manager.add_custom_term(
            "azithromycin", 
            ["as throw my sin", "azthr my sin"], 
            "medication"
        )
        
        # Check if term was added
        self.assertEqual(len(self.vocab_manager.custom_terms), 1)
        
        # Check term details
        key = "medication:azithromycin"
        self.assertIn(key, self.vocab_manager.custom_terms)
        term_data = self.vocab_manager.custom_terms[key]
        self.assertEqual(term_data['correct'], "azithromycin")
        self.assertEqual(term_data['category'], "medication")
        self.assertIn("as throw my sin", term_data['variations'])
    
    def test_apply_corrections(self):
        """Test applying vocabulary corrections to text."""
        # Add a test term
        self.vocab_manager.add_custom_term(
            "azithromycin", 
            ["as throw my sin"], 
            "medication"
        )
        
        # Test correction
        test_text = "Person needs as throw my sin 500mg daily"
        corrected_text, corrections = self.vocab_manager.apply_corrections(test_text)
        
        self.assertEqual(corrected_text, "Person needs azithromycin 500mg daily")
        self.assertEqual(len(corrections), 1)
        self.assertEqual(corrections[0]['original'], "as throw my sin")
        self.assertEqual(corrections[0]['corrected'], "azithromycin")
    
    def test_learn_from_correction(self):
        """Test learning from user corrections."""
        # Learn a correction
        learned = self.vocab_manager.learn_from_correction(
            "new motor ax", 
            "pneumothorax", 
            "person has pneumothorax"
        )
        
        self.assertTrue(learned)
        self.assertEqual(len(self.vocab_manager.correction_history), 1)
        
        # Learn the same correction again (should promote to custom term)
        self.vocab_manager.learn_from_correction(
            "new motor ax", 
            "pneumothorax", 
            "another pneumothorax case"
        )
        
        # Should now be in custom terms
        self.assertGreater(len(self.vocab_manager.custom_terms), 0)
    
    def test_case_preservation(self):
        """Test that case is preserved in corrections."""
        self.vocab_manager.add_custom_term("Azithromycin", ["azith mycin"])
        
        test_cases = [
            ("AZITH MYCIN", "AZITHROMYCIN"),
            ("azith mycin", "azithromycin"),
            ("Azith Mycin", "Azithromycin")
        ]
        
        for original, expected in test_cases:
            corrected_text, _ = self.vocab_manager.apply_corrections(original)
            self.assertEqual(corrected_text, expected)
    
    def test_categorization(self):
        """Test automatic categorization of terms."""
        # Test medication pattern
        category = self.vocab_manager._categorize_term("azithromycin")
        self.assertEqual(category, "medication")
        
        # Test doctor name pattern
        category = self.vocab_manager._categorize_term("Dr. Smith")
        self.assertEqual(category, "names")
        
        # Test technical condition pattern
        category = self.vocab_manager._categorize_term("pneumonia")
        self.assertEqual(category, "technical_terms")
    
    def test_vocabulary_stats(self):
        """Test vocabulary statistics."""
        # Add some terms
        self.vocab_manager.add_custom_term("azithromycin", [], "medication")
        self.vocab_manager.add_custom_term("Dr. Smith", [], "names")
        
        stats = self.vocab_manager.get_vocabulary_stats()
        
        self.assertEqual(stats['total_terms'], 2)
        self.assertEqual(stats['categories']['medication'], 1)
        self.assertEqual(stats['categories']['names'], 1)
    
    def test_suggestions(self):
        """Test correction suggestions."""
        # Add some terms
        self.vocab_manager.add_custom_term("azithromycin", [], "medication")
        self.vocab_manager.add_custom_term("acetaminophen", [], "medication")
        
        # Test suggestions for similar words
        suggestions = self.vocab_manager.suggest_corrections("azithro")
        
        self.assertGreater(len(suggestions), 0)
        self.assertEqual(suggestions[0]['suggested'], "azithromycin")


class TestVocabularyAPI(unittest.TestCase):
    """Test the vocabulary API interface."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        # Create API with temporary directory
        from vocabulary.vocabulary_manager import VocabularyManager
        self.vocab_manager = VocabularyManager(config_dir=self.test_dir)
        self.api = VocabularyAPI()
        self.api.vocab_manager = self.vocab_manager
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
    
    def test_add_term_api(self):
        """Test adding terms via API."""
        result = self.api.add_term(
            "azithromycin", 
            ["as throw my sin"], 
            "medication"
        )
        
        self.assertTrue(result['success'])
        self.assertIn("Added term", result['message'])
    
    def test_get_vocabulary_list_api(self):
        """Test getting vocabulary list via API."""
        # Add a term
        self.api.add_term("azithromycin", ["as throw my sin"], "medication")
        
        # Get list
        result = self.api.get_vocabulary_list()
        
        self.assertTrue(result['success'])
        self.assertEqual(len(result['terms']), 1)
        self.assertEqual(result['terms'][0]['correct'], "azithromycin")
    
    def test_get_stats_api(self):
        """Test getting statistics via API."""
        # Add some terms
        self.api.add_term("azithromycin", [], "medication")
        self.api.add_term("Dr. Smith", [], "names")
        
        result = self.api.get_vocabulary_stats()
        
        self.assertTrue(result['success'])
        self.assertEqual(result['stats']['total_terms'], 2)
    
    def test_command_handler(self):
        """Test the command handler interface."""
        # Test add term command
        result = handle_vocabulary_command(
            "add_term",
            correct_term="azithromycin",
            variations=["as throw my sin"],
            category="medication"
        )
        
        self.assertTrue(result['success'])
        
        # Test get list command
        result = handle_vocabulary_command("get_list")
        
        self.assertTrue(result['success'])
        self.assertEqual(len(result['terms']), 1)
    
    def test_error_handling(self):
        """Test error handling in API."""
        # Test unknown command
        result = handle_vocabulary_command("unknown_command")
        
        self.assertFalse(result['success'])
        self.assertIn("Unknown vocabulary command", result['error'])


class TestVocabularyIntegration(unittest.TestCase):
    """Test vocabulary system integration."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.vocab_manager = VocabularyManager(config_dir=self.test_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
    
    def test_persistence(self):
        """Test that vocabulary persists across sessions."""
        # Add term and save
        self.vocab_manager.add_custom_term("azithromycin", ["as throw my sin"])
        
        # Create new manager instance (simulating restart)
        new_manager = VocabularyManager(config_dir=self.test_dir)
        
        # Check if term persisted
        self.assertEqual(len(new_manager.custom_terms), 1)
        self.assertIn("general:azithromycin", new_manager.custom_terms)
    
    def test_learning_workflow(self):
        """Test the complete learning workflow."""
        # Start with a transcription error
        original_text = "Person has new motor ax"
        
        # User corrects it
        self.vocab_manager.learn_from_correction("new motor ax", "pneumothorax")
        
        # Correct again (should promote to custom term)
        self.vocab_manager.learn_from_correction("new motor ax", "pneumothorax")
        
        # Now it should auto-correct
        corrected_text, corrections = self.vocab_manager.apply_corrections(original_text)
        
        self.assertEqual(corrected_text, "Person has pneumothorax")
        self.assertEqual(len(corrections), 1)
    
    def test_template_import_simulation(self):
        """Test template import functionality."""
        # Create a mock template file
        template_data = {
            "vocabulary_export": {
                "terms": {
                    "medication:azithromycin": {
                        "correct": "azithromycin",
                        "variations": ["as throw my sin"],
                        "category": "medication",
                        "added_date": "2025-01-07T00:00:00",
                        "usage_count": 0
                    }
                }
            }
        }
        
        template_path = os.path.join(self.test_dir, "test_template.json")
        import json
        with open(template_path, 'w') as f:
            json.dump(template_data, f)
        
        # Import template
        success = self.vocab_manager.import_vocabulary(template_path)
        
        self.assertTrue(success)
        self.assertEqual(len(self.vocab_manager.custom_terms), 1)
        self.assertEqual(
            self.vocab_manager.custom_terms["medication:azithromycin"]["correct"], 
            "azithromycin"
        )


if __name__ == '__main__':
    unittest.main() 