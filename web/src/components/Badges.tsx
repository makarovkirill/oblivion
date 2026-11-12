import React from 'react';
import { Shield, ShieldAlert, CheckCircle, AlertCircle, Radio, Skull } from 'lucide-react';
import { useLanguage } from '../locales/LanguageContext';
import { SwitchState } from '../types';

export const WindowsAdminBadge: React.FC<{ isAdmin: boolean }> = ({ isAdmin }) => {
  const { t } = useLanguage();
  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
        isAdmin
          ? 'bg-emerald-950/40 text-emerald-400 border-emerald-800/60'
          : 'bg-gray-800/50 text-gray-400 border-gray-700/60'
      }`}
    >
      {isAdmin ? <Shield className="w-3.5 h-3.5 text-emerald-400" /> : <ShieldAlert className="w-3.5 h-3.5 text-gray-400" />}
      <span>{isAdmin ? t('adminBadgeElevated') : t('adminBadgeStandard')}</span>
    </div>
  );
};

export const TaskSchedulerBadge: React.FC<{ registered: boolean }> = ({ registered }) => {
  const { t } = useLanguage();
  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
        registered
          ? 'bg-blue-950/40 text-blue-400 border-blue-800/60'
          : 'bg-amber-950/40 text-amber-400 border-amber-800/60'
      }`}
    >
      {registered ? <CheckCircle className="w-3.5 h-3.5 text-blue-400" /> : <AlertCircle className="w-3.5 h-3.5 text-amber-400" />}
      <span>{registered ? t('schedulerRegistered') : t('schedulerNotRegistered')}</span>
    </div>
  );
};

export const TelegramBotBadge: React.FC<{ connected: boolean; username?: string | null }> = ({
  connected,
  username,
}) => {
  const { t } = useLanguage();
  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
        connected
          ? 'bg-sky-950/40 text-sky-400 border-sky-800/60'
          : 'bg-gray-800/50 text-gray-400 border-gray-700/60'
      }`}
    >
      <Radio className={`w-3.5 h-3.5 ${connected ? 'text-sky-400 animate-pulse' : 'text-gray-500'}`} />
      <span>
        {connected ? `${t('botOnline')}${username ? ` (@${username})` : ''}` : t('botOffline')}
      </span>
    </div>
  );
};

export const SwitchStatusBadge: React.FC<{ status: SwitchState }> = ({ status }) => {
  const { t } = useLanguage();
  if (status === 'ACTIVE') {
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
        {t('statusActive')}
      </span>
    );
  }
  if (status === 'GRACE_PERIOD') {
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-bounce">
        <AlertCircle className="w-4 h-4 text-amber-400" />
        {t('statusGrace')}
      </span>
    );
  }
  if (status === 'TRIGGERED') {
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-bold bg-red-500/10 text-red-400 border border-red-500/20">
        <Skull className="w-4 h-4 text-red-400" />
        {t('statusTriggered')}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center px-3 py-1 rounded-md text-xs font-bold bg-gray-700/30 text-gray-400 border border-gray-700/40">
      {t('statusNotConfigured')}
    </span>
  );
};
