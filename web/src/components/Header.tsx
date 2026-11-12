import React from 'react';
import { Lock, Unlock, ShieldAlert, Languages } from 'lucide-react';
import { useLanguage } from '../locales/LanguageContext';
import { SystemStatusResponse } from '../types';
import { WindowsAdminBadge, TaskSchedulerBadge, TelegramBotBadge, SwitchStatusBadge } from './Badges';

interface HeaderProps {
  statusData: SystemStatusResponse | null;
  onOpenUnlock: () => void;
  onLockVault: () => void;
}

export const Header: React.FC<HeaderProps> = ({ statusData, onOpenUnlock, onLockVault }) => {
  const { language, setLanguage, t } = useLanguage();
  const isUnlocked = statusData?.switch.unlocked_session ?? false;

  return (
    <header className="bg-surface/80 backdrop-blur border-b border-border sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-blue-600/10 border border-blue-500/20 text-blue-400">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-black text-gray-100 tracking-wider">OBLIVION</h1>
              <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 font-mono border border-blue-500/20 font-bold">RELEASE</span>
            </div>
            <p className="text-xs text-gray-400 font-mono">{t('appSubtitle')}</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {statusData && (
            <>
              <SwitchStatusBadge status={statusData.switch.status} />
              <WindowsAdminBadge isAdmin={statusData.windows.is_admin} />
              <TaskSchedulerBadge registered={statusData.windows.task_scheduler.registered} />
              <TelegramBotBadge
                connected={statusData.telegram.connected}
                username={statusData.telegram.username}
              />
            </>
          )}

          <div className="flex items-center border border-border rounded-lg overflow-hidden bg-card/60 ml-0 sm:ml-1">
            <button
              onClick={() => setLanguage('en')}
              className={`px-2.5 py-1 text-xs font-semibold flex items-center gap-1 transition ${
                language === 'en' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              <Languages className="w-3 h-3" />
              EN
            </button>
            <button
              onClick={() => setLanguage('ru')}
              className={`px-2.5 py-1 text-xs font-semibold transition ${
                language === 'ru' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              RU
            </button>
          </div>

          {statusData?.switch.setup_completed && (
            <button
              onClick={isUnlocked ? onLockVault : onOpenUnlock}
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium border transition whitespace-nowrap ${
                isUnlocked
                  ? 'bg-emerald-950/40 text-emerald-300 border-emerald-800/80 hover:bg-emerald-900/40'
                  : 'bg-card text-gray-300 border-border hover:bg-gray-800'
              }`}
            >
              {isUnlocked ? (
                <>
                  <Unlock className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                  <span>{t('lockVault')}</span>
                </>
              ) : (
                <>
                  <Lock className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
                  <span>{t('unlockVault')}</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
