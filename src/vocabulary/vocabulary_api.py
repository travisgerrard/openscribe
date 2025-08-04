"""
Vocabulary API for Frontend-Backend Communication
Provides functions that can be called from the main app to handle vocabulary operations
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from .vocabulary_manager import get_vocabulary_manager


class VocabularyAPI:
    """API interface for vocabulary management operations."""
    
    def __init__(self):
        self.vocab_manager = get_vocabulary_manager()
    
    def add_term(self, correct_term: str, variations: List[str], category: str = "general") -> Dict[str, Any]:
        """Add a new custom term."""
        try:
            self.vocab_manager.add_custom_term(correct_term, variations, category)
            return {
                "success": True,
                "message": f"Added term '{correct_term}' with {len(variations)} variations"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_vocabulary_list(self, search_filter: str = "", category_filter: str = "") -> Dict[str, Any]:
        """Get the current vocabulary list with optional filtering."""
        try:
            terms = []
            for key, term_data in self.vocab_manager.custom_terms.items():
                # Apply filters
                if search_filter and search_filter.lower() not in term_data['correct'].lower():
                    continue
                if category_filter and term_data['category'] != category_filter:
                    continue
                
                terms.append({
                    'key': key,
                    'correct': term_data['correct'],
                    'variations': term_data['variations'],
                    'category': term_data['category'],
                    'usage_count': term_data['usage_count'],
                    'added_date': term_data.get('added_date', '')
                })
            
            # Sort by usage count (most used first), then alphabetically
            terms.sort(key=lambda x: (-x['usage_count'], x['correct'].lower()))
            
            return {
                "success": True,
                "terms": terms,
                "total_count": len(terms)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_vocabulary_stats(self) -> Dict[str, Any]:
        """Get vocabulary statistics."""
        try:
            stats = self.vocab_manager.get_vocabulary_stats()
            return {
                "success": True,
                "stats": stats
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def edit_term(self, term_key: str, category: str = None, additional_variations: List[str] = None, remove_variations: List[str] = None) -> Dict[str, Any]:
        """Edit an existing vocabulary term by adding/removing variations or changing category."""
        try:
            if term_key not in self.vocab_manager.custom_terms:
                return {
                    "success": False,
                    "error": "Term not found"
                }
            
            term_data = self.vocab_manager.custom_terms[term_key]
            term_name = term_data['correct']
            changes_made = []
            
            # Update category if provided
            if category and category != term_data['category']:
                old_category = term_data['category']
                term_data['category'] = category
                changes_made.append(f"category changed from '{old_category}' to '{category}'")
            
            # Remove variations if specified
            if remove_variations:
                removed_variations = []
                for variation in remove_variations:
                    if variation in term_data['variations']:
                        term_data['variations'].remove(variation)
                        removed_variations.append(variation)
                
                if removed_variations:
                    changes_made.append(f"removed {len(removed_variations)} variations: {', '.join(removed_variations)}")
            
            # Add new variations if provided
            if additional_variations:
                # Filter out empty variations and duplicates
                new_variations = [v.strip() for v in additional_variations if v.strip()]
                existing_variations = set(v.lower() for v in term_data['variations'])
                
                added_variations = []
                for variation in new_variations:
                    if variation.lower() not in existing_variations:
                        term_data['variations'].append(variation)
                        existing_variations.add(variation.lower())
                        added_variations.append(variation)
                
                if added_variations:
                    changes_made.append(f"added {len(added_variations)} new variations: {', '.join(added_variations)}")
            
            if changes_made:
                self.vocab_manager.save_vocabulary()
                return {
                    "success": True,
                    "message": f"Updated term '{term_name}': {'; '.join(changes_made)}"
                }
            else:
                return {
                    "success": True,
                    "message": f"No changes made to term '{term_name}'"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def delete_term(self, term_key: str) -> Dict[str, Any]:
        """Delete a vocabulary term."""
        try:
            if term_key in self.vocab_manager.custom_terms:
                term_name = self.vocab_manager.custom_terms[term_key]['correct']
                del self.vocab_manager.custom_terms[term_key]
                self.vocab_manager.save_vocabulary()
                return {
                    "success": True,
                    "message": f"Deleted term '{term_name}'"
                }
            else:
                return {
                    "success": False,
                    "error": "Term not found"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def import_template(self, template_name: str) -> Dict[str, Any]:
        """Import a vocabulary template."""
        try:
            template_path = Path(f"data/vocabulary_templates/{template_name}.json")
            
            if not template_path.exists():
                return {
                    "success": False,
                    "error": f"Template '{template_name}' not found"
                }
            
            success = self.vocab_manager.import_vocabulary(str(template_path), merge=True)
            
            if success:
                return {
                    "success": True,
                    "message": f"Successfully imported '{template_name}' template"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to import template"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def export_vocabulary(self, filepath: str) -> Dict[str, Any]:
        """Export vocabulary to a file."""
        try:
            success = self.vocab_manager.export_vocabulary(filepath)
            
            if success:
                return {
                    "success": True,
                    "message": f"Vocabulary exported to {filepath}"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to export vocabulary"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def clear_vocabulary(self) -> Dict[str, Any]:
        """Clear all vocabulary terms."""
        try:
            term_count = len(self.vocab_manager.custom_terms)
            self.vocab_manager.custom_terms = {}
            self.vocab_manager.learning_patterns = {}
            self.vocab_manager.save_vocabulary()
            
            return {
                "success": True,
                "message": f"Cleared {term_count} vocabulary terms"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def learn_correction(self, original: str, corrected: str, context: str = "") -> Dict[str, Any]:
        """Learn from a user correction."""
        try:
            learned = self.vocab_manager.learn_from_correction(original, corrected, context)
            
            if learned:
                return {
                    "success": True,
                    "message": f"Learned correction: '{original}' → '{corrected}'"
                }
            else:
                return {
                    "success": True,
                    "message": "No correction needed (terms are identical)"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_suggestions(self, text: str, max_suggestions: int = 3) -> Dict[str, Any]:
        """Get correction suggestions for text."""
        try:
            suggestions = self.vocab_manager.suggest_corrections(text, max_suggestions)
            
            return {
                "success": True,
                "suggestions": suggestions
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Global API instance
_vocabulary_api = None

def get_vocabulary_api() -> VocabularyAPI:
    """Get the global vocabulary API instance."""
    global _vocabulary_api
    if _vocabulary_api is None:
        _vocabulary_api = VocabularyAPI()
    return _vocabulary_api


# Convenience functions for direct calling from main app
def handle_vocabulary_command(command: str, **kwargs) -> Dict[str, Any]:
    """Handle vocabulary commands from the main application."""
    api = get_vocabulary_api()
    
    if command == "add_term":
        return api.add_term(
            kwargs.get("correct_term", ""),
            kwargs.get("variations", []),
            kwargs.get("category", "general")
        )
    
    elif command == "get_list":
        return api.get_vocabulary_list(
            kwargs.get("search", ""),
            kwargs.get("category", "")
        )
    
    elif command == "get_stats":
        return api.get_vocabulary_stats()
    
    elif command == "edit_term":
        return api.edit_term(
            kwargs.get("term_key", ""),
            kwargs.get("category"),
            kwargs.get("additional_variations", []),
            kwargs.get("remove_variations", [])
        )
    
    elif command == "delete_term":
        return api.delete_term(kwargs.get("term_key", ""))
    
    elif command == "import_template":
        return api.import_template(kwargs.get("template_name", ""))
    
    elif command == "export":
        return api.export_vocabulary(kwargs.get("filepath", ""))
    
    elif command == "clear_all":
        return api.clear_vocabulary()
    
    elif command == "learn_correction":
        return api.learn_correction(
            kwargs.get("original", ""),
            kwargs.get("corrected", ""),
            kwargs.get("context", "")
        )
    
    elif command == "get_suggestions":
        return api.get_suggestions(
            kwargs.get("text", ""),
            kwargs.get("max_suggestions", 3)
        )
    
    else:
        return {
            "success": False,
            "error": f"Unknown vocabulary command: {command}"
        } 