// src/services/history.js
import { httpClient } from './http';

export const historyService = {
  /**
   * Fetches user history from the server.
   * For authenticated users, it fetches history from the database.
   * For anonymous users, it returns the session-stored history.
   */
  async getUserHistory() {
    try {
      const response = await httpClient.get('/user/history');
      return response;
    } catch (error) {
      console.error('Error fetching user history:', error);
      // Return empty history on error
      return { 
        history: [], 
        user_authenticated: false,
        error: error.message
      };
    }
  },

  /**
   * Saves a history item to the server.
   * For authenticated users, it saves to the database.
   * For anonymous users, it saves to the session.
   * 
   * @param {Object} data - The history item data to save
   * @param {string} data.title - The title of the lesson
   * @param {string} data.resourceType - The type of resource
   * @param {Object} data.lessonData - The full lesson data
   */
  async saveHistoryItem(data) {
    try {
      const response = await httpClient.post('/user/history', data);
      return response;
    } catch (error) {
      console.error('Error saving history item:', error);
      throw error;
    }
  },

  /**
   * Track lesson generation for history.
   * This is a convenience method that formats the data and calls saveHistoryItem.
   * 
   * @param {Object} formState - The form state with lesson details
   * @param {Object} contentState - The content state with structured content
   */
  async trackLessonGeneration(formState, contentState) {
    try {
      const historyItem = {
        title: formState.lessonTopic || formState.subjectFocus || 'Untitled Lesson',
        resourceType: formState.resourceType || 'PRESENTATION',
        lessonData: {
          ...formState,
          structuredContent: contentState.structuredContent,
          finalOutline: contentState.finalOutline
        }
      };
      
      return await this.saveHistoryItem(historyItem);
    } catch (error) {
      console.error('Error tracking lesson generation:', error);
      // Continue even if tracking fails
      return { success: false, error: error.message };
    }
  },
  
  /**
   * Gets the history from local storage for anonymous users.
   * This is a fallback if the session storage on the server isn't available.
   */
  getLocalHistory() {
    try {
      const localHistory = localStorage.getItem('anonymous_history');
      return localHistory ? JSON.parse(localHistory) : [];
    } catch (error) {
      console.error('Error reading local history:', error);
      return [];
    }
  },
  
  /**
   * Saves history to local storage for anonymous users.
   * This is a fallback if the session storage on the server isn't available.
   * 
   * @param {Object} historyItem - The history item to save
   */
  saveLocalHistory(historyItem) {
    try {
      let history = this.getLocalHistory();
      
      // Add new item to the beginning of the array
      history.unshift(historyItem);
      
      // Limit to 10 items
      if (history.length > 10) {
        history = history.slice(0, 10);
      }
      
      localStorage.setItem('anonymous_history', JSON.stringify(history));
      return true;
    } catch (error) {
      console.error('Error saving local history:', error);
      return false;
    }
  },
  
  /**
   * Clears local history for anonymous users.
   */
  clearLocalHistory() {
    localStorage.removeItem('anonymous_history');
  }
};

export default historyService;
