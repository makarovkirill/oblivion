import React, { useState } from 'react';
import { X, KeyRound, ShieldAlert, CheckCircle2, Loader2 } from 'lucide-react';
import { useLanguage } from '../locales/LanguageContext';
import { api } from '../api';

interface CheckInModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const CheckInModal: React.FC<CheckInModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const { t } = useLanguage();
  const [passphrase, setPassphrase] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  if (!isOpen) return null;

  const isLengthValid = passphrase.length >= 16;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isLengthValid) {
      setError(t('passphraseTooShort'));
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await api.checkIn(passphrase);
      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        setPassphrase('');
        onSuccess();
        onClose();
      }, 1200);
    } catch (err: any) {
      setError(err.message || 'Check-in failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
      <div className="bg-surface border border-border rounded-2xl w-full max-w-md overflow-hidden shadow-2xl">
        <div className="p-5 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-blue-600/10 text-blue-400 border border-blue-500/20">
              <KeyRound className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-gray-100">{t('checkInModalTitle')}</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-card transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <p className="text-xs text-gray-400 leading-relaxed">
            {t('checkInModalDesc')}
          </p>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold text-gray-300">
                {t('passphraseLabel')}
              </label>
              <span className={`text-[11px] font-mono font-medium ${
                isLengthValid ? 'text-emerald-400' : 'text-amber-400'
              }`}>
                {passphrase.length} / 16 {isLengthValid ? '✓' : `(${16 - passphrase.length} more)`}
              </span>
            </div>
            <input
              type="password"
              value={passphrase}
              onChange={(e) => {
                setPassphrase(e.target.value);
                setError(null);
              }}
              placeholder={t('passphrasePlaceholder')}
              autoFocus
              className="w-full px-3.5 py-2.5 rounded-xl bg-card border border-border text-gray-100 placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500 font-mono transition"
            />
          </div>

          {error && (
            <div className="p-3 rounded-xl bg-red-950/40 border border-red-800/80 text-red-300 text-xs flex items-start gap-2">
              <ShieldAlert className="w-4 h-4 flex-shrink-0 text-red-400 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="p-3 rounded-xl bg-emerald-950/40 border border-emerald-800/80 text-emerald-300 text-xs flex items-center gap-2 font-medium">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Activity confirmed. Watchdog countdown restarted.</span>
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
              disabled={loading || !isLengthValid || success}
              className={`px-5 py-2 rounded-xl text-xs font-bold text-white flex items-center gap-2 shadow-lg transition active:scale-95 ${
                loading || !isLengthValid || success
                  ? 'bg-gray-800 text-gray-500 cursor-not-allowed border border-gray-700'
                  : 'bg-blue-600 hover:bg-blue-500 shadow-blue-600/20'
              }`}
            >
              {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              <span>{t('confirmCheckInBtn')}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
