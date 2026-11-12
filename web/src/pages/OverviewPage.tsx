import React from 'react';
import { Shield, Users, Database, FileText, Activity } from 'lucide-react';
import { useLanguage } from '../locales/LanguageContext';
import { SwitchStatus, AuditLog, WindowsSecurityContext } from '../types';
import { CountdownTimer } from '../components/CountdownTimer';

interface OverviewPageProps {
  switchData: SwitchStatus;
  windowsData: WindowsSecurityContext;
  vaultCount: number;
  contactsCount: number;
  logs: AuditLog[];
  onOpenCheckIn: () => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({
  switchData,
  windowsData,
  vaultCount,
  contactsCount,
  logs,
  onOpenCheckIn,
}) => {
  const { t } = useLanguage();

  return (
    <div className="space-y-6">
      <CountdownTimer switchData={switchData} onOpenCheckIn={onOpenCheckIn} />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl bg-surface border border-border flex items-center justify-between">
          <div>
            <span className="text-xs text-gray-400 block font-medium">{t('cardVaultItems')}</span>
            <span className="text-2xl font-bold font-mono text-gray-100">{vaultCount}</span>
            <span className="text-[11px] text-gray-500 block mt-0.5">{t('cardEncryptedAssets')}</span>
          </div>
          <div className="p-3 rounded-xl bg-blue-600/10 text-blue-400 border border-blue-500/20">
            <Database className="w-5 h-5" />
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-surface border border-border flex items-center justify-between">
          <div>
            <span className="text-xs text-gray-400 block font-medium">{t('cardBeneficiaries')}</span>
            <span className="text-2xl font-bold font-mono text-gray-100">{contactsCount}</span>
            <span className="text-[11px] text-gray-500 block mt-0.5">{t('cardSplitKeyEscrow')}</span>
          </div>
          <div className="p-3 rounded-xl bg-emerald-600/10 text-emerald-400 border border-emerald-500/20">
            <Users className="w-5 h-5" />
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-surface border border-border flex items-center justify-between">
          <div>
            <span className="text-xs text-gray-400 block font-medium">{t('cardWindowsPrivileges')}</span>
            <span className="text-lg font-bold text-gray-100 font-mono">
              {windowsData.is_admin ? t('cardPrivilegeHighest') : t('cardPrivilegeStandard')}
            </span>
            <span className="text-[11px] text-gray-500 block mt-0.5">
              {windowsData.is_admin ? t('cardElevatedShredding') : t('cardStandardToken')}
            </span>
          </div>
          <div className="p-3 rounded-xl bg-purple-600/10 text-purple-400 border border-purple-500/20">
            <Shield className="w-5 h-5" />
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-surface border border-border flex items-center justify-between">
          <div>
            <span className="text-xs text-gray-400 block font-medium">{t('cardWatchdogService')}</span>
            <span className="text-lg font-bold text-gray-100 font-mono">
              {windowsData.task_scheduler.registered ? t('cardServiceReady') : t('cardServiceInactive')}
            </span>
            <span className="text-[11px] text-gray-500 block mt-0.5">
              {windowsData.task_scheduler.registered ? t('cardServiceRunning') : (windowsData.task_scheduler.status || 'Inactive')}
            </span>
          </div>
          <div className="p-3 rounded-xl bg-sky-600/10 text-sky-400 border border-sky-500/20">
            <Activity className="w-5 h-5" />
          </div>
        </div>
      </div>

      <div className="p-6 rounded-2xl bg-surface border border-border">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-gray-400" />
            <h3 className="font-bold text-sm text-gray-200">{t('auditLogsTitle')}</h3>
          </div>
          <span className="text-xs text-gray-500 font-mono">{t('liveSecurityEvents')}</span>
        </div>

        <div className="overflow-x-auto">
          {logs.length === 0 ? (
            <p className="text-xs text-gray-500 py-4 text-center">{t('noLogs')}</p>
          ) : (
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-border text-gray-400">
                  <th className="pb-2.5 font-medium">{t('tableTime')}</th>
                  <th className="pb-2.5 font-medium">{t('tableEvent')}</th>
                  <th className="pb-2.5 font-medium">{t('tableDetails')}</th>
                  <th className="pb-2.5 font-medium text-right">{t('tableSeverity')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40 font-mono">
                {logs.slice(0, 10).map((l) => (
                  <tr key={l.id} className="hover:bg-card/40 transition">
                    <td className="py-2.5 text-gray-400 whitespace-nowrap">
                      {new Date(l.timestamp * 1000).toLocaleTimeString()}
                    </td>
                    <td className="py-2.5 text-gray-200 font-semibold">{l.event_type}</td>
                    <td className="py-2.5 text-gray-400 max-w-md truncate">{l.details}</td>
                    <td className="py-2.5 text-right whitespace-nowrap">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                          l.severity === 'DANGER'
                            ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                            : l.severity === 'WARNING'
                            ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                            : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        }`}
                      >
                        {l.severity}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};
