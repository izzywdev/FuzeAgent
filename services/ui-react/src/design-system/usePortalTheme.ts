import { useState, useEffect } from 'react';

export type PortalTheme = 'dark' | 'light';

export function getPortalTheme(): PortalTheme {
  if (typeof document === 'undefined') return 'dark';
  
  // 1. Check data-theme attribute on <html> set by FuzeFront shell
  const attr = document.documentElement.getAttribute('data-theme');
  if (attr === 'light' || attr === 'dark') return attr as PortalTheme;

  // 2. Check classList
  if (document.documentElement.classList.contains('light')) return 'light';
  if (document.documentElement.classList.contains('dark')) return 'dark';

  // 3. Check localStorage
  try {
    const saved = localStorage.getItem('theme');
    if (saved === 'light' || saved === 'dark') return saved as PortalTheme;
  } catch {
    // ignore
  }

  return 'dark'; // Dark is the default fuse seam theme
}

export function usePortalTheme() {
  const [theme, setThemeState] = useState<PortalTheme>(getPortalTheme);

  useEffect(() => {
    // Apply theme attribute
    const applyTheme = (newTheme: PortalTheme) => {
      setThemeState(newTheme);
      if (typeof document !== 'undefined') {
        document.documentElement.setAttribute('data-theme', newTheme);
        if (newTheme === 'dark') {
          document.documentElement.classList.add('dark');
          document.documentElement.classList.remove('light');
        } else {
          document.documentElement.classList.add('light');
          document.documentElement.classList.remove('dark');
        }
      }
    };

    // Initial check
    applyTheme(getPortalTheme());

    // Observe host shell changes to <html data-theme="...">
    const observer = new MutationObserver(() => {
      const current = getPortalTheme();
      if (current !== theme) {
        setThemeState(current);
      }
    });

    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme', 'class'],
    });

    // Listen to localStorage changes across tabs/frames
    const handleStorage = (e: StorageEvent) => {
      if (e.key === 'theme' && (e.newValue === 'light' || e.newValue === 'dark')) {
        applyTheme(e.newValue as PortalTheme);
      }
    };
    window.addEventListener('storage', handleStorage);

    return () => {
      observer.disconnect();
      window.removeEventListener('storage', handleStorage);
    };
  }, []);

  const setTheme = (newTheme: PortalTheme) => {
    setThemeState(newTheme);
    try {
      localStorage.setItem('theme', newTheme);
    } catch { /* ignore: best-effort localStorage persistence */ }
    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('data-theme', newTheme);
      if (newTheme === 'dark') {
        document.documentElement.classList.add('dark');
        document.documentElement.classList.remove('light');
      } else {
        document.documentElement.classList.add('light');
        document.documentElement.classList.remove('dark');
      }
    }
  };

  const toggleTheme = () => {
    setTheme(theme === 'dark' ? 'light' : 'dark');
  };

  return {
    theme,
    isDark: theme === 'dark',
    isLight: theme === 'light',
    setTheme,
    toggleTheme,
  };
}
