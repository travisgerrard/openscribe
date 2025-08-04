"""
Vocabulary Management System
Handles custom vocabulary, corrections, and adaptive learning for CitrixTranscriber
"""

import json
import re
import os
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import difflib
from datetime import datetime


class VocabularyManager:
    """Manages custom vocabulary and learning from user corrections."""
    
    def __init__(self, config_dir: str = "data"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # File paths
        self.vocabulary_file = self.config_dir / "user_vocabulary.json"
        self.corrections_log = self.config_dir / "corrections_log.json"
        self.learning_stats = self.config_dir / "learning_stats.json"
        
        # In-memory storage
        self.custom_terms: Dict[str, List[str]] = {}
        self.correction_history: List[Dict] = []
        self.learning_patterns: Dict[str, int] = {}
        
        # Load existing data
        self.load_vocabulary()
        self.load_corrections()
    
    def load_vocabulary(self) -> None:
        """Load custom vocabulary from file."""
        try:
            if self.vocabulary_file.exists():
                with open(self.vocabulary_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.custom_terms = data.get('terms', {})
                    self.learning_patterns = data.get('patterns', {})
        except Exception as e:
            print(f"[VOCAB] Error loading vocabulary: {e}")
            self.custom_terms = {}
            self.learning_patterns = {}
    
    def save_vocabulary(self) -> None:
        """Save current vocabulary to file."""
        try:
            data = {
                'terms': self.custom_terms,
                'patterns': self.learning_patterns,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.vocabulary_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[VOCAB] Error saving vocabulary: {e}")
    
    def load_corrections(self) -> None:
        """Load correction history from file."""
        try:
            if self.corrections_log.exists():
                with open(self.corrections_log, 'r', encoding='utf-8') as f:
                    self.correction_history = json.load(f)
        except Exception as e:
            print(f"[VOCAB] Error loading corrections: {e}")
            self.correction_history = []
    
    def save_corrections(self) -> None:
        """Save correction history to file."""
        try:
            with open(self.corrections_log, 'w', encoding='utf-8') as f:
                json.dump(self.correction_history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[VOCAB] Error saving corrections: {e}")
    
    def add_custom_term(self, correct_term: str, variations: Optional[List[str]] = None, 
                       category: str = "general") -> None:
        """Add a custom term with its variations."""
        if variations is None:
            variations = []
        
        # Ensure correct term is in the variations list
        if correct_term not in variations:
            variations.insert(0, correct_term)
        
        # Store with category prefix for organization
        key = f"{category}:{correct_term.lower()}"
        self.custom_terms[key] = {
            'correct': correct_term,
            'variations': variations,
            'category': category,
            'added_date': datetime.now().isoformat(),
            'usage_count': 0
        }
        
        self.save_vocabulary()
        print(f"[VOCAB] Added term: {correct_term} with {len(variations)} variations")
    
    def learn_from_correction(self, original: str, corrected: str, context: str = "") -> bool:
        """Learn from a user correction."""
        if original.strip() == corrected.strip():
            return False
        
        # Log the correction
        correction_entry = {
            'original': original,
            'corrected': corrected,
            'context': context,
            'timestamp': datetime.now().isoformat(),
            'confidence': self._calculate_confidence(original, corrected)
        }
        
        self.correction_history.append(correction_entry)
        
        # Update learning patterns
        pattern_key = f"{original.lower()} -> {corrected.lower()}"
        self.learning_patterns[pattern_key] = self.learning_patterns.get(pattern_key, 0) + 1
        
        # If this correction appears frequently, add it as a custom term
        if self.learning_patterns[pattern_key] >= 2:  # After 2 corrections, make it permanent
            self._promote_to_custom_term(original, corrected)
        
        self.save_corrections()
        self.save_vocabulary()
        
        print(f"[VOCAB] Learned correction: '{original}' → '{corrected}' (count: {self.learning_patterns[pattern_key]})")
        return True
    
    def _calculate_confidence(self, original: str, corrected: str) -> float:
        """Calculate confidence score for a correction based on similarity."""
        similarity = difflib.SequenceMatcher(None, original.lower(), corrected.lower()).ratio()
        return round(similarity, 2)
    
    def _promote_to_custom_term(self, original: str, corrected: str) -> None:
        """Promote a frequently corrected term to custom vocabulary."""
        # Determine category based on context or content
        category = self._categorize_term(corrected)
        
        # Check if we already have this term
        existing_key = None
        for key, term_data in self.custom_terms.items():
            if term_data['correct'].lower() == corrected.lower():
                existing_key = key
                break
        
        if existing_key:
            # Add to existing variations
            if original not in self.custom_terms[existing_key]['variations']:
                self.custom_terms[existing_key]['variations'].append(original)
        else:
            # Create new term
            self.add_custom_term(corrected, [original], category)
    
    def _categorize_term(self, term: str) -> str:
        """Attempt to categorize a term based on patterns."""
        term_lower = term.lower()
        
        # Technical/medication patterns
        if any(suffix in term_lower for suffix in ['mycin', 'cillin', 'phen', 'zole', 'pine']):
            return "medication"
        
        # Professional titles
        if term.startswith(('Dr.', 'Doctor', 'Mr.', 'Mrs.', 'Ms.', 'Prof.', 'Professor')):
            return "names"
        
        # Technical procedures/conditions (common suffixes and specific terms)
        technical_patterns = ['itis', 'osis', 'emia', 'pathy', 'gram', 'scopy', 'monia', 'thorax', 'tension']
        if any(suffix in term_lower for suffix in technical_patterns):
            return "technical_terms"
        
        return "general"
    
    def apply_corrections(self, text: str) -> Tuple[str, List[Dict]]:
        """Apply vocabulary corrections to text and return corrected text + correction info."""
        corrected_text = text
        applied_corrections = []
        
        for key, term_data in self.custom_terms.items():
            correct_term = term_data['correct']
            variations = term_data['variations']
            
            for variation in variations:
                if variation.lower() in corrected_text.lower():
                    # Use regex for whole word replacement
                    pattern = r'\b' + re.escape(variation) + r'\b'
                    matches = list(re.finditer(pattern, corrected_text, re.IGNORECASE))
                    
                    for match in reversed(matches):  # Reverse to maintain positions
                        # Replace while preserving original case pattern
                        replacement = self._preserve_case(match.group(), correct_term)
                        corrected_text = corrected_text[:match.start()] + replacement + corrected_text[match.end():]
                        
                        applied_corrections.append({
                            'original': match.group(),
                            'corrected': replacement,
                            'position': match.start(),
                            'category': term_data['category']
                        })
                        
                        # Update usage count
                        self.custom_terms[key]['usage_count'] += 1
        
        if applied_corrections:
            self.save_vocabulary()  # Save updated usage counts
        
        return corrected_text, applied_corrections
    
    def _preserve_case(self, original: str, replacement: str) -> str:
        """Preserve the case pattern of the original when replacing."""
        if original.isupper():
            return replacement.upper()
        elif original.islower():
            return replacement.lower()
        elif original.istitle():
            return replacement.title()
        else:
            return replacement
    
    def suggest_corrections(self, text: str, max_suggestions: int = 3) -> List[Dict]:
        """Suggest possible corrections for text based on learned patterns."""
        suggestions = []
        words = text.split()
        
        for word in words:
            # Find close matches in our vocabulary
            best_matches = difflib.get_close_matches(
                word.lower(), 
                [term_data['correct'].lower() for term_data in self.custom_terms.values()],
                n=max_suggestions,
                cutoff=0.6
            )
            
            for match in best_matches:
                # Find the original term data
                for term_data in self.custom_terms.values():
                    if term_data['correct'].lower() == match:
                        suggestions.append({
                            'original': word,
                            'suggested': term_data['correct'],
                            'confidence': difflib.SequenceMatcher(None, word.lower(), match).ratio(),
                            'category': term_data['category'],
                            'usage_count': term_data['usage_count']
                        })
                        break
        
        # Sort by confidence and usage
        suggestions.sort(key=lambda x: (x['confidence'], x['usage_count']), reverse=True)
        return suggestions[:max_suggestions]
    
    def get_vocabulary_stats(self) -> Dict:
        """Get statistics about the vocabulary system."""
        categories = {}
        total_usage = 0
        
        for term_data in self.custom_terms.values():
            category = term_data['category']
            categories[category] = categories.get(category, 0) + 1
            total_usage += term_data['usage_count']
        
        return {
            'total_terms': len(self.custom_terms),
            'categories': categories,
            'total_corrections': len(self.correction_history),
            'total_usage': total_usage,
            'learning_patterns': len(self.learning_patterns)
        }
    
    def export_vocabulary(self, filepath: str) -> bool:
        """Export vocabulary to a shareable file."""
        try:
            export_data = {
                'vocabulary_export': {
                    'terms': self.custom_terms,
                    'export_date': datetime.now().isoformat(),
                    'stats': self.get_vocabulary_stats()
                }
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            print(f"[VOCAB] Exported vocabulary to {filepath}")
            return True
        except Exception as e:
            print(f"[VOCAB] Error exporting vocabulary: {e}")
            return False
    
    def import_vocabulary(self, filepath: str, merge: bool = True) -> bool:
        """Import vocabulary from a file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            imported_terms = data.get('vocabulary_export', {}).get('terms', {})
            
            if merge:
                # Merge with existing vocabulary
                self.custom_terms.update(imported_terms)
            else:
                # Replace existing vocabulary
                self.custom_terms = imported_terms
            
            self.save_vocabulary()
            print(f"[VOCAB] Imported {len(imported_terms)} terms from {filepath}")
            return True
        except Exception as e:
            print(f"[VOCAB] Error importing vocabulary: {e}")
            return False


# Global instance
_vocabulary_manager = None

def get_vocabulary_manager() -> VocabularyManager:
    """Get the global vocabulary manager instance."""
    global _vocabulary_manager
    if _vocabulary_manager is None:
        _vocabulary_manager = VocabularyManager()
    return _vocabulary_manager 