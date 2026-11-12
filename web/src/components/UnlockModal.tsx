import React, { useState } from 'react';
import { X, Lock, ShieldAlert, Loader2 } from 'lucide-react';
import { useLanguage } from '../locales/LanguageContext';
import { api } from '../api';

interface UnlockModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const UnlockModal: React.FC<UnlockModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const { t } = useLanguage();
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password) return;

    setLoading(true);
    setError(null);

    try {
      await api.unlockVault(password);
      setPassword('');
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Unlock failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
      <div className="bg-surface border border-border rounded-2xl w-full max-w-sm overflow-hidden shadow-2xl">
        <div className="p-5 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-blue-600/10 text-blue-400 border border-blue-500/20">
              <Lock className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-gray-100">{t('unlockVault')}</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-card transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-300 mb-1.5">
              {t('masterPasswordLabel')}
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setError(null);
              }}
              placeholder="Enter master password..."
              autoFocus
              className="w-full px-3.5 py-2.5 rounded-xl bg-card border border-border text-gray-100 placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500 transition"
            />
          </div>

          {error && (
            <div className="p-3 rounded-xl bg-red-950/40 border border-red-800/80 text-red-300 text-xs flex items-start gap-2">
              <ShieldAlert className="w-4 h-4 flex-shrink-0 text-red-400 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <div className="pt-2 flex items-center justify-end gap-2.5">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-gray-300 hover:text-gray-100 hover:bg-card rounded-xl transition"
            >
              {t('cancelBtn')}
            </button>
            <button
              type="submit"
              disabled={loading || !password}
              className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-blue-600 hover:bg-blue-500 flex items-center gap-2 shadow-lg transition active:scale-95 disabled:opacity-50"
            >
              {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              <span>{t('unlockVault')}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
