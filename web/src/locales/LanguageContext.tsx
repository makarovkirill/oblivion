import React, { createContext, useContext, useState } from 'react';
import { Language } from '../types';
import enDict from './en.json';
import ruDict from './ru.json';

type TranslationKey = keyof typeof enDict;

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: TranslationKey) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<Language>(() => {
    const saved = localStorage.getItem('oblivion_lang');
    return (saved === 'ru' || saved === 'en') ? saved : 'en';
  });

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    localStorage.setItem('oblivion_lang', lang);
  };

  const t = (key: TranslationKey): string => {
    const dict: Record<string, string> = language === 'ru' ? ruDict : enDict;
    return dict[key] || (enDict as Record<string, string>)[key] || key;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = (): LanguageContextType => {
  const ctx = useContext(LanguageContext);
  if (!ctx) {
    throw new Error('useLanguage must be used within LanguageProvider');
  }
  return ctx;
};
