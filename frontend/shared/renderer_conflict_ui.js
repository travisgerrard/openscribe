// renderer_conflict_ui.js
// Handles the prominent microphone conflict notification banner UI

class ConflictNotificationManager {
  constructor() {
    this.banner = document.getElementById('mic-conflict-banner');
    this.conflictMessage = document.getElementById('conflict-message');
    this.dismissButton = document.getElementById('conflict-dismiss');

    this.isVisible = false;
    this.dismissTimer = null;
    this.autoHideTimer = null;

    this.setupEventListeners();
  }

  setupEventListeners() {
    // Handle dismiss button click
    if (this.dismissButton) {
      this.dismissButton.addEventListener('click', () => {
        this.hideConflictBanner();
      });
    }

    // Auto-hide after 10 seconds if user doesn't dismiss
    this.setupAutoHide();
  }

  setupAutoHide() {
    // Clear any existing timer
    if (this.autoHideTimer) {
      clearTimeout(this.autoHideTimer);
    }

    // Auto-hide after 15 seconds (give user time to read and understand)
    this.autoHideTimer = setTimeout(() => {
      if (this.isVisible) {
        this.hideConflictBanner();
      }
    }, 15000);
  }

  showConflictBanner(conflictDetails) {
    if (!this.banner || !this.conflictMessage) {
      console.warn('Conflict banner elements not found');
      return;
    }

    // Update the message with specific conflict details
    if (conflictDetails) {
      this.conflictMessage.textContent = conflictDetails;
    }

    // Show the banner
    this.banner.classList.remove('hidden');
    this.banner.classList.add('visible');
    document.body.classList.add('conflict-banner-visible');

    this.isVisible = true;

    // Set up auto-hide timer
    this.setupAutoHide();

    console.log('Microphone conflict banner shown:', conflictDetails);
  }

  hideConflictBanner() {
    if (!this.banner) {
      return;
    }

    // Hide the banner
    this.banner.classList.remove('visible');
    this.banner.classList.add('hidden');
    document.body.classList.remove('conflict-banner-visible');

    this.isVisible = false;

    // Clear timers
    if (this.autoHideTimer) {
      clearTimeout(this.autoHideTimer);
      this.autoHideTimer = null;
    }

    console.log('Microphone conflict banner hidden');
  }

  updateConflictMessage(newMessage) {
    if (this.conflictMessage) {
      this.conflictMessage.textContent = newMessage;
    }

    // If banner is not visible but we're getting updates, show it
    if (!this.isVisible) {
      this.showConflictBanner(newMessage);
    } else {
      // Reset auto-hide timer since we got new information
      this.setupAutoHide();
    }
  }

  isConflictVisible() {
    return this.isVisible;
  }
}

// Create global instance
const conflictNotificationManager = new ConflictNotificationManager();

// Export for use in other modules
export { conflictNotificationManager };

// Also make it available globally for debugging
window.conflictNotificationManager = conflictNotificationManager;