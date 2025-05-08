import React, { useState, useEffect } from 'react';
import { Box, Typography, Chip, CircularProgress, Alert } from '@mui/material';
import { FileText, Presentation, BookOpen, FileQuestion, FileSpreadsheet, Files } from 'lucide-react';
import { historyService } from '../../services/history';
import { useAuth } from '../../contexts/AuthContext';

const RESOURCE_TYPES = {
  PRESENTATION: {
    icon: Presentation,
    color: '#2563eb',
    label: 'Presentation'
  },
  QUIZ: {
    icon: FileQuestion,
    color: '#dc2626',
    label: 'Quiz'
  },
  LESSON_PLAN: {
    icon: BookOpen,
    color: '#059669',
    label: 'Lesson Plan'
  },
  WORKSHEET: {
    icon: FileSpreadsheet,
    color: '#7c3aed',
    label: 'Worksheet'
  },
  ALL_OPTIONS: {
    icon: Files,
    color: '#d97706',
    label: 'All Options'
  }
};

// Default to FileText icon for unknown resource types
const getResourceTypeInfo = (resourceType) => {
  const typeKey = resourceType?.toUpperCase?.() || 'PRESENTATION';
  return RESOURCE_TYPES[typeKey] || {
    icon: FileText,
    color: '#4b5563',
    label: resourceType || 'Resource'
  };
};

const RecentItem = ({ item, onClick }) => {
  // Extract info from the history item
  const title = item.title || 'Untitled Lesson';
  // Handle both string and array formats for types
  const types = Array.isArray(item.types) ? item.types : [item.types || 'PRESENTATION'];
  const date = item.date || 'Today';
  
  // Get resource info for the primary type
  const primaryType = types[0]?.toUpperCase?.() || 'PRESENTATION';
  const resourceType = getResourceTypeInfo(primaryType);
  const Icon = resourceType.icon;

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 1.5,  // Reduced gap
        p: 1.5,    // Reduced padding
        borderRadius: '6px',
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        '&:hover': {
          backgroundColor: '#f3f4f6'
        }
      }}
      onClick={() => onClick && onClick(item)}
    >
      <Icon size={16} color={resourceType.color} />
      <Box sx={{ flex: 1 }}>
        <Typography sx={{ 
          fontSize: '0.75rem',  // Reduced font size
          color: '#374151',
          fontWeight: '500',
          mb: 0.5  // Reduced margin
        }}>
          {title}
        </Typography>
        <Box sx={{ 
          display: 'flex',
          flexWrap: 'wrap',
          gap: 0.5,  // Reduced gap
          mb: 0.5   // Reduced margin
        }}>
          {types.map((type, index) => {
            const typeInfo = getResourceTypeInfo(type);
            return (
              <Chip
                key={index}
                label={typeInfo.label}
                size="small"
                sx={{
                  height: '20px',  // Smaller chip height
                  fontSize: '0.625rem',  // Smaller font size
                  backgroundColor: `${typeInfo.color}15`,
                  color: typeInfo.color,
                  fontWeight: '500'
                }}
              />
            );
          })}
        </Box>
        <Typography sx={{ 
          fontSize: '0.625rem',  // Reduced font size
          color: '#6b7280'
        }}>
          {date}
        </Typography>
      </Box>
    </Box>
  );
};

const RecentsList = ({ onSelectItem }) => {
  const [historyItems, setHistoryItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    // Function to fetch history
    const fetchHistory = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Fetch history from server
        const response = await historyService.getUserHistory();
        
        if (response.error) {
          throw new Error(response.error);
        }
        
        // If authenticated user and history returned
        if (response.history && Array.isArray(response.history)) {
          setHistoryItems(response.history);
        } 
        // For anonymous users, try to get from local storage as fallback
        else if (!isAuthenticated) {
          const localHistory = historyService.getLocalHistory();
          setHistoryItems(localHistory);
        }
      } catch (err) {
        console.error('Error fetching history:', err);
        setError('Failed to load history. Please try again later.');
        
        // Use local storage as fallback
        if (!isAuthenticated) {
          const localHistory = historyService.getLocalHistory();
          setHistoryItems(localHistory);
        }
      } finally {
        setLoading(false);
      }
    };
    
    fetchHistory();
  }, [isAuthenticated]);  // Re-fetch when auth state changes

  const handleItemClick = (item) => {
    if (onSelectItem) {
      onSelectItem(item);
    }
  };

  return (
    <Box sx={{ mt: 2, px: 1 }}>
      <Typography 
        variant="h6" 
        sx={{ 
          mb: 1,
          px: 1.5,
          color: '#4b5563',
          fontSize: '0.875rem',
          fontWeight: '600'
        }}
      >
        Recent Resources
      </Typography>
      
      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress size={24} />
        </Box>
      )}
      
      {error && (
        <Alert 
          severity="error" 
          sx={{ 
            mx: 1.5, 
            mb: 2,
            fontSize: '0.75rem' 
          }}
        >
          {error}
        </Alert>
      )}
      
      {!loading && !error && historyItems.length === 0 && (
        <Box sx={{ p: 1.5, textAlign: 'center' }}>
          <Typography 
            sx={{ 
              fontSize: '0.75rem',
              color: '#6b7280',
              fontStyle: 'italic'
            }}
          >
            No recent activities yet.
            {!isAuthenticated && (
              <Box component="span" sx={{ display: 'block', mt: 0.5 }}>
                Sign in to save your history.
              </Box>
            )}
          </Typography>
        </Box>
      )}
      
      {historyItems.map((item, index) => (
        <RecentItem 
          key={item.id || index} 
          item={item} 
          onClick={() => handleItemClick(item)}
        />
      ))}
    </Box>
  );
};

export default RecentsList;
