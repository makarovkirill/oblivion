import React from 'react';
import { Clock, AlertTriangle, KeyRound } from 'lucide-react';
import { useLanguage } from '../locales/LanguageContext';
import { SwitchStatus } from '../types';

interface CountdownTimerProps {
  switchData: SwitchStatus;
  onOpenCheckIn: () => void;
}

export const CountdownTimer: React.FC<CountdownTimerProps> = ({ switchData, onOpenCheckIn }) => {
  const { t } = useLanguage();
  const remaining = Math.max(0, switchData.remaining_seconds);

  const days = Math.floor(remaining / 86400);
  const hours = Math.floor((remaining % 86400) / 3600);
  const minutes = Math.floor((remaining % 3600) / 60);
  const seconds = remaining % 60;

  const totalPeriod = (switchData.interval_seconds || 604800) + (switchData.grace_seconds || 86400);
  const progressPercent = Math.min(100, Math.max(0, (remaining / totalPeriod) * 100));

  const isGrace = switchData.status === 'GRACE_PERIOD';
  const isTriggered = switchData.status === 'TRIGGERED';

  return (
    <div className={`p-6 rounded-2xl border transition relative overflow-hidden ${
      isTriggered
        ? 'bg-red-950/20 border-red-800/80'
        : isGrace
        ? 'bg-amber-950/20 border-amber-500/80 shadow-[0_0_25px_rgba(245,158,11,0.15)]'
        : 'bg-surface border-border'
    }`}>
      {isGrace && (
        <div className="mb-4 p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center gap-3 text-amber-300 text-sm animate-pulse">
          <AlertTriangle className="w-5 h-5 flex-shrink-0 text-amber-400" />
          <span>{t('graceWarningNotice')}</span>
        </div>
      )}

      <div className="flex flex-col md:flex-row items-center justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 text-gray-400 text-sm font-medium mb-1">
            <Clock className="w-4 h-4 text-blue-400" />
            <span>{t('countdownTitle')}</span>
          </div>
          <p className="text-xs text-gray-500">
            {t('lastCheckIn')}: <span className="text-gray-300 font-mono">{switchData.last_checkin_str || '-'}</span>
          </p>
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          <div className="flex flex-col items-center bg-card/80 border border-border px-3 py-2 sm:px-4 sm:py-3 rounded-xl min-w-[64px]">
            <span className="text-2xl sm:text-3xl font-extrabold font-mono text-gray-100">{String(days).padStart(2, '0')}</span>
            <span className="text-[10px] text-gray-400 uppercase tracking-wider">{t('days')}</span>
          </div>
          <span className="text-xl font-mono text-gray-600">:</span>
          <div className="flex flex-col items-center bg-card/80 border border-border px-3 py-2 sm:px-4 sm:py-3 rounded-xl min-w-[64px]">
            <span className="text-2xl sm:text-3xl font-extrabold font-mono text-gray-100">{String(hours).padStart(2, '0')}</span>
            <span className="text-[10px] text-gray-400 uppercase tracking-wider">{t('hours')}</span>
          </div>
          <span className="text-xl font-mono text-gray-600">:</span>
          <div className="flex flex-col items-center bg-card/80 border border-border px-3 py-2 sm:px-4 sm:py-3 rounded-xl min-w-[64px]">
            <span className="text-2xl sm:text-3xl font-extrabold font-mono text-gray-100">{String(minutes).padStart(2, '0')}</span>
            <span className="text-[10px] text-gray-400 uppercase tracking-wider">{t('minutes')}</span>
          </div>
          <span className="text-xl font-mono text-gray-600">:</span>
          <div className="flex flex-col items-center bg-card/80 border border-border px-3 py-2 sm:px-4 sm:py-3 rounded-xl min-w-[64px]">
            <span className={`text-2xl sm:text-3xl font-extrabold font-mono ${isGrace ? 'text-amber-400' : 'text-blue-400'}`}>
              {String(seconds).padStart(2, '0')}
            </span>
            <span className="text-[10px] text-gray-400 uppercase tracking-wider">{t('seconds')}</span>
          </div>
        </div>

        <div>
          <button
            onClick={onOpenCheckIn}
            disabled={isTriggered}
            className={`w-full sm:w-auto px-5 py-3 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 shadow-lg transition active:scale-95 ${
              isTriggered
                ? 'bg-gray-800 text-gray-500 cursor-not-allowed border border-gray-700'
                : isGrace
                ? 'bg-amber-500 hover:bg-amber-400 text-gray-950 font-bold shadow-amber-500/20'
                : 'bg-blue-600 hover:bg-blue-500 text-white shadow-blue-600/20'
            }`}
          >
            <KeyRound className="w-4 h-4" />
            <span>{t('checkInButton')}</span>
          </button>
        </div>
      </div>

      <div className="mt-6 pt-4 border-t border-border/50 flex flex-col sm:flex-row sm:items-center justify-between text-xs text-gray-400 gap-2">
        <div className="flex items-center gap-4">
          <span>{t('nextCheckInDeadline')}: <strong className="text-gray-200 font-mono">{switchData.next_deadline_str || '-'}</strong></span>
          <span>{t('graceDeadline')}: <strong className="text-gray-200 font-mono">{switchData.grace_deadline_str || '-'}</strong></span>
        </div>
        <div className="w-full sm:w-48 bg-gray-800 rounded-full h-2 overflow-hidden border border-gray-700">
          <div
            className={`h-full transition-all duration-500 ${
              isGrace ? 'bg-amber-400' : 'bg-blue-500'
            }`}
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>
    </div>
  );
};
