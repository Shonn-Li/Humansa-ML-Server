import { TestStatus, LogLevel } from '../types';

// Date formatting utilities
export const formatDate = (date: string | Date): string => {
  const d = new Date(date);
  return d.toLocaleDateString() + ' ' + d.toLocaleTimeString();
};

export const formatDateShort = (date: string | Date): string => {
  const d = new Date(date);
  return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

export const formatRelativeTime = (date: string | Date): string => {
  const d = new Date(date);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} minutes ago`;
  if (hours < 24) return `${hours} hours ago`;
  return `${days} days ago`;
};

// Duration formatting
export const formatDuration = (milliseconds: number): string => {
  if (milliseconds < 1000) {
    return `${milliseconds}ms`;
  }
  
  const seconds = milliseconds / 1000;
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  
  const minutes = seconds / 60;
  if (minutes < 60) {
    return `${minutes.toFixed(1)}m`;
  }
  
  const hours = minutes / 60;
  return `${hours.toFixed(1)}h`;
};

// Status utilities
export const getStatusColor = (status: TestStatus): string => {
  switch (status) {
    case TestStatus.PASSED:
      return 'text-green-600 bg-green-50';
    case TestStatus.FAILED:
      return 'text-red-600 bg-red-50';
    case TestStatus.SKIPPED:
      return 'text-yellow-600 bg-yellow-50';
    case TestStatus.PENDING:
      return 'text-gray-600 bg-gray-50';
    case TestStatus.RUNNING:
      return 'text-blue-600 bg-blue-50';
    default:
      return 'text-gray-600 bg-gray-50';
  }
};

export const getStatusIcon = (status: TestStatus): string => {
  switch (status) {
    case TestStatus.PASSED:
      return '✓';
    case TestStatus.FAILED:
      return '✗';
    case TestStatus.SKIPPED:
      return '⊝';
    case TestStatus.PENDING:
      return '○';
    case TestStatus.RUNNING:
      return '⟳';
    default:
      return '?';
  }
};

export const getLogLevelColor = (level: LogLevel): string => {
  switch (level) {
    case LogLevel.DEBUG:
      return 'text-gray-500';
    case LogLevel.INFO:
      return 'text-blue-600';
    case LogLevel.WARNING:
      return 'text-yellow-600';
    case LogLevel.ERROR:
      return 'text-red-600';
    default:
      return 'text-gray-600';
  }
};

// Data transformation utilities
export const calculateSuccessRate = (passed: number, total: number): number => {
  if (total === 0) return 0;
  return Math.round((passed / total) * 100);
};

export const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
};

export const formatNumber = (num: number): string => {
  return new Intl.NumberFormat().format(num);
};

export const formatPercentage = (value: number, total: number): string => {
  if (total === 0) return '0%';
  return `${Math.round((value / total) * 100)}%`;
};

// String utilities
export const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + '...';
};

export const highlightText = (text: string, query: string): string => {
  if (!query) return text;
  
  const regex = new RegExp(`(${query})`, 'gi');
  return text.replace(regex, '<mark>$1</mark>');
};

// URL utilities
export const buildApiUrl = (endpoint: string, params?: Record<string, any>): string => {
  const url = new URL(endpoint, window.location.origin);
  
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.append(key, value.toString());
      }
    });
  }
  
  return url.toString();
};

// Export utilities
export const downloadFile = (blob: Blob, filename: string): void => {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

export const generateFileName = (
  prefix: string,
  extension: string,
  timestamp?: Date
): string => {
  const date = timestamp || new Date();
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const seconds = String(date.getSeconds()).padStart(2, '0');
  
  const dateStr = `${year}-${month}-${day}_${hours}-${minutes}-${seconds}`;
  return `${prefix}_${dateStr}.${extension}`;
};

// Classification utilities
export const classifyTestName = (name: string): string => {
  const lower = name.toLowerCase();
  
  if (lower.includes('appointment') || lower.includes('booking')) {
    return 'appointment';
  }
  if (lower.includes('product') || lower.includes('recommendation')) {
    return 'product';
  }
  if (lower.includes('emergency') || lower.includes('urgent')) {
    return 'emergency';
  }
  if (lower.includes('multi') || lower.includes('conversation')) {
    return 'multi_turn';
  }
  if (lower.includes('edge') || lower.includes('error')) {
    return 'edge_case';
  }
  
  return 'general';
};

// Debounce utility
export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout;
  
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
};

// Local storage utilities
export const saveToLocalStorage = (key: string, value: any): void => {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    console.warn('Failed to save to localStorage:', error);
  }
};

export const loadFromLocalStorage = <T>(key: string, defaultValue: T): T => {
  try {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : defaultValue;
  } catch (error) {
    console.warn('Failed to load from localStorage:', error);
    return defaultValue;
  }
};

// CSS class utility
export const cn = (...classes: (string | undefined | null | false)[]): string => {
  return classes.filter(Boolean).join(' ');
};