import React, { useState, useEffect } from 'react';
import {
  Clock,
  Radio,
  Mail,
  Send,
  PlayCircle,
  Flame,
  Save,
  CheckCircle2,
  Loader2,
  Lock
} from 'lucide-react';
import { useLanguage } from '../locales/LanguageContext';
import { SettingsData } from '../types';
import { api } from '../api';
import { PanicModal } from './PanicModal';
import { SimulateModal } from './SimulateModal';

interface SettingsPageProps {
  onRefreshStatus: () => void;
  onOpenUnlock: () => void;
  isUnlocked: boolean;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({
  onRefreshStatus,
  onOpenUnlock,
  isUnlocked,
}) => {
  const { t } = useLanguage();
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const [intervalSec, setIntervalSec] = useState(604800);
  const [graceSec, setGraceSec] = useState(86400);
  const [newUninstallKey, setNewUninstallKey] = useState('');

  const [telegramToken, setTelegramToken] = useState('');
  const [telegramChatId, setTelegramChatId] = useState('');
  const [testPingLoading, setTestPingLoading] = useState(false);
  const [testPingResult, setTestPingResult] = useState<{ success: boolean; msg: string } | null>(null);

  const [smtpHost, setSmtpHost] = useState('');
  const [smtpPort, setSmtpPort] = useState(587);
  const [smtpUser, setSmtpUser] = useState('');
  const [smtpPass, setSmtpPass] = useState('');
  const [smtpFrom, setSmtpFrom] = useState('');
  const [smtpUseTls, setSmtpUseTls] = useState(true);
  const [testEmailLoading, setTestEmailLoading] = useState(false);
  const [testEmailResult, setTestEmailResult] = useState<{ success: boolean; msg: string } | null>(null);

  const [showSimulateModal, setShowSimulateModal] = useState(false);
  const [simulationPlan, setSimulationPlan] = useState<any>(null);
  const [simulating, setSimulating] = useState(false);

  const [showPanicModal, setShowPanicModal] = useState(false);

  useEffect(() => {
    if (isUnlocked) {
      loadSettings();
    }
  }, [isUnlocked]);

  const loadSettings = async () => {
    try {
      const data = await api.getSettings();
      setSettings(data);
      setIntervalSec(data.checkin_interval_sec);
      setGraceSec(data.grace_period_sec);
      setTelegramChatId(data.telegram_owner_chat_id);
      setSmtpHost(data.smtp_host);
      setSmtpPort(data.smtp_port);
      setSmtpUser(data.smtp_user);
      setSmtpFrom(data.smtp_from);
      setSmtpUseTls(data.smtp_use_tls);
    } catch (err: any) {
      console.error('Failed to load settings:', err);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaveSuccess(false);

    try {
      const payload: any = {
        checkin_interval_sec: intervalSec,
        grace_period_sec: graceSec,
        telegram_owner_chat_id: telegramChatId,
        smtp_host: smtpHost,
        smtp_port: smtpPort,
        smtp_user: smtpUser,
        smtp_from: smtpFrom,
        smtp_use_tls: smtpUseTls,
      };

      if (telegramToken.trim()) {
        payload.telegram_bot_token = telegramToken.trim();
      }
      if (smtpPass) {
        payload.smtp_password = smtpPass;
      }
      if (newUninstallKey.trim().length >= 4) {
        payload.uninstall_key = newUninstallKey.trim();
      }

      await api.updateSettings(payload);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2500);
      onRefreshStatus();
      loadSettings();
    } catch (err: any) {
      alert(err.message || 'Failed to update settings');
    } finally {
      setSaving(false);
    }
  };

  const handleTestPing = async () => {
    const token = telegramToken.trim() || (settings?.has_telegram_token ? 'KEEP_CURRENT' : '');
    const chatId = telegramChatId.trim();
    if (!chatId) return;

    setTestPingLoading(true);
    setTestPingResult(null);

    try {
      const res = await api.testTelegram(token, chatId);
      setTestPingResult({ success: true, msg: res.message || t('testPingSuccess') });
    } catch (err: any) {
      setTestPingResult({ success: false, msg: err.message || 'Telegram test failed' });
    } finally {
      setTestPingLoading(false);
    }
  };

  const handleTestEmail = async () => {
    if (!smtpHost || !smtpFrom) return;
    setTestEmailLoading(true);
    setTestEmailResult(null);

    try {
      const res = await api.testEmail({
        host: smtpHost,
        port: smtpPort,
        user: smtpUser,
        password: smtpPass,
        from_addr: smtpFrom,
        target_email: smtpFrom,
        use_tls: smtpUseTls,
      });
      setTestEmailResult({ success: true, msg: res.message || 'Email sent successfully' });
    } catch (err: any) {
      setTestEmailResult({ success: false, msg: err.message || 'SMTP test failed' });
    } finally {
      setTestEmailLoading(false);
    }
  };

  const handleSimulate = async () => {
    setSimulating(true);
    try {
      const res = await api.simulateTrigger();
      setSimulationPlan(res.plan);
      setShowSimulateModal(true);
    } catch (err: any) {
      alert(err.message || 'Simulation failed');
    } finally {
      setSimulating(false);
    }
  };

  if (!isUnlocked) {
    return (
      <div className="p-8 rounded-2xl bg-surface border border-border text-center space-y-4">
        <Radio className="w-10 h-10 text-gray-500 mx-auto" />
        <h3 className="font-bold text-gray-200">Settings are Locked</h3>
        <p className="text-xs text-gray-400 max-w-md mx-auto">
          Please unlock your vault using your Master Password to inspect and modify security configurations.
        </p>
        <button
          onClick={onOpenUnlock}
          className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-blue-600 hover:bg-blue-500 transition"
        >
          {t('unlockVault')}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-lg font-bold text-gray-100">{t('settingsTitle')}</h2>
        <p className="text-xs text-gray-400">Configure timer thresholds, background notifications, and emergency triggers.</p>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        <div className="p-6 rounded-2xl bg-surface border border-border space-y-4">
          <div className="flex items-center gap-2 text-sm font-bold text-gray-100">
            <Clock className="w-4 h-4 text-blue-400" />
            <span>{t('timerSetupTitle')}</span>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-2">
                {t('inactivityIntervalLabel')}
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                {[
                  { label: t('preset7Days'), sec: 604800 },
                  { label: t('preset14Days'), sec: 1209600 },
                  { label: t('preset30Days'), sec: 2592000 },
                  { label: t('preset90Days'), sec: 7776000 },
                  { label: t('presetTest1m'), sec: 60 },
                  { label: t('presetTest5m'), sec: 300 },
                ].map((p) => (
                  <button
                    key={p.sec}
                    type="button"
                    onClick={() => setIntervalSec(p.sec)}
                    className={`p-3 rounded-xl border text-left text-xs font-medium transition ${
                      intervalSec === p.sec
                        ? 'bg-blue-600/10 border-blue-500 text-blue-300 ring-1 ring-blue-500/30'
                        : 'bg-card border-border text-gray-400 hover:border-gray-600'
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-2">
                {t('gracePeriodLabel')}
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                {[
                  { label: t('gracePreset24h'), sec: 86400 },
                  { label: t('gracePreset48h'), sec: 172800 },
                  { label: t('gracePresetTest30s'), sec: 30 },
                  { label: t('gracePresetTest1m'), sec: 60 },
                ].map((p) => (
                  <button
                    key={p.sec}
                    type="button"
                    onClick={() => setGraceSec(p.sec)}
                    className={`p-3 rounded-xl border text-left text-xs font-medium transition ${
                      graceSec === p.sec
                        ? 'bg-amber-500/10 border-amber-500 text-amber-300 ring-1 ring-amber-500/30'
                        : 'bg-card border-border text-gray-400 hover:border-gray-600'
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="p-6 rounded-2xl bg-surface border border-border space-y-4">
          <div className="flex items-center gap-2 text-sm font-bold text-gray-100">
            <Lock className="w-4 h-4 text-emerald-400" />
            <span>{t('uninstallKeyLabel')}</span>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-300 mb-1">{t('uninstallKeyLabel')}</label>
            <input
              type="text"
              value={newUninstallKey}
              onChange={(e) => setNewUninstallKey(e.target.value)}
              placeholder="Leave blank to keep existing..."
              className="w-full sm:w-80 px-3 py-2 rounded-xl bg-card border border-border text-gray-100 text-xs font-mono focus:outline-none focus:border-blue-500"
            />
            <p className="text-[11px] text-gray-500 mt-1">{t('uninstallKeyHint')}</p>
          </div>
        </div>

        <div className="p-6 rounded-2xl bg-surface border border-border space-y-4">
          <div className="flex items-center gap-2 text-sm font-bold text-gray-100">
            <Radio className="w-4 h-4 text-sky-400" />
            <span>{t('telegramSetupTitle')}</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1">{t('botTokenLabel')}</label>
              <input
                type="text"
                value={telegramToken}
                onChange={(e) => setTelegramToken(e.target.value)}
                placeholder={settings?.telegram_bot_token_masked || t('botTokenPlaceholder')}
                className="w-full px-3 py-2 rounded-xl bg-card border border-border text-gray-100 text-xs font-mono focus:outline-none focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1">{t('ownerChatIdLabel')}</label>
              <input
                type="text"
                value={telegramChatId}
                onChange={(e) => setTelegramChatId(e.target.value)}
                placeholder="123456789"
                className="w-full px-3 py-2 rounded-xl bg-card border border-border text-gray-100 text-xs font-mono focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {telegramChatId && (
            <div className="flex items-center gap-3 pt-1">
              <button
                type="button"
                onClick={handleTestPing}
                disabled={testPingLoading}
                className="px-3.5 py-1.5 rounded-xl text-xs font-bold text-white bg-sky-600 hover:bg-sky-500 flex items-center gap-2 shadow-lg transition active:scale-95 disabled:opacity-50"
              >
                {testPingLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                <span>{t('testPingBtn')}</span>
              </button>
              {testPingResult && (
                <span className={`text-xs ${testPingResult.success ? 'text-emerald-400' : 'text-red-400'}`}>
                  {testPingResult.msg}
                </span>
              )}
            </div>
          )}
        </div>

        <div className="p-6 rounded-2xl bg-surface border border-border space-y-4">
          <div className="flex items-center gap-2 text-sm font-bold text-gray-100">
            <Mail className="w-4 h-4 text-emerald-400" />
            <span>{t('optionalSmtpTitle')}</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="sm:col-span-2">
              <label className="text-[11px] text-gray-400 block mb-1">{t('smtpHostLabel')}</label>
              <input
                type="text"
                value={smtpHost}
                onChange={(e) => setSmtpHost(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg bg-card border border-border text-xs text-gray-100"
              />
            </div>
            <div>
              <label className="text-[11px] text-gray-400 block mb-1">{t('smtpPortLabel')}</label>
              <input
                type="number"
                value={smtpPort}
                onChange={(e) => setSmtpPort(Number(e.target.value))}
                className="w-full px-3 py-1.5 rounded-lg bg-card border border-border text-xs text-gray-100 font-mono"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-[11px] text-gray-400 block mb-1">{t('smtpUserLabel')}</label>
              <input
                type="text"
                value={smtpUser}
                onChange={(e) => setSmtpUser(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg bg-card border border-border text-xs text-gray-100"
              />
            </div>
            <div>
              <label className="text-[11px] text-gray-400 block mb-1">{t('smtpPassLabel')}</label>
              <input
                type="password"
                value={smtpPass}
                onChange={(e) => setSmtpPass(e.target.value)}
                placeholder="Leave blank to keep existing..."
                className="w-full px-3 py-1.5 rounded-lg bg-card border border-border text-xs text-gray-100"
              />
            </div>
          </div>

          <div>
            <label className="text-[11px] text-gray-400 block mb-1">{t('smtpFromLabel')}</label>
            <input
              type="text"
              value={smtpFrom}
              onChange={(e) => setSmtpFrom(e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg bg-card border border-border text-xs text-gray-100"
            />
          </div>

          {smtpHost && smtpFrom && (
            <div className="flex items-center gap-3 pt-1">
              <button
                type="button"
                onClick={handleTestEmail}
                disabled={testEmailLoading}
                className="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-gray-700 hover:bg-gray-600 text-gray-200 flex items-center gap-2 transition"
              >
                {testEmailLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>{t('testEmailBtn')}</span>
              </button>
              {testEmailResult && (
                <span className={`text-xs ${testEmailResult.success ? 'text-emerald-400' : 'text-red-400'}`}>
                  {testEmailResult.msg}
                </span>
              )}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between pt-2">
          {saveSuccess && (
            <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
              <span>OBLIVION settings updated successfully!</span>
            </div>
          )}
          <div className="ml-auto">
            <button
              type="submit"
              disabled={saving}
              className="px-6 py-2.5 rounded-xl text-xs font-bold text-white bg-blue-600 hover:bg-blue-500 flex items-center gap-2 shadow-lg transition active:scale-95 disabled:opacity-50"
            >
              {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
              <span>{t('updateSettingsBtn')}</span>
            </button>
          </div>
        </div>
      </form>

      <div className="p-6 rounded-2xl bg-surface border border-red-900/50 space-y-6">
        <div>
          <h3 className="text-base font-bold text-red-300">Emergency Controls</h3>
          <p className="text-xs text-gray-400">Perform safe dry-run simulations or trigger emergency data erasure.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-5 rounded-2xl bg-card border border-border flex flex-col justify-between space-y-4">
            <div className="space-y-1.5">
              <div className="flex items-center gap-2 font-bold text-sm text-gray-100">
                <PlayCircle className="w-4 h-4 text-blue-400" />
                <span>{t('simulateTriggerBtn')}</span>
              </div>
              <p className="text-xs text-gray-400 leading-relaxed">
                {t('simulateTriggerDesc')}
              </p>
            </div>
            <button
              onClick={handleSimulate}
              disabled={simulating}
              className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-blue-600/80 hover:bg-blue-600 flex items-center justify-center gap-2 transition"
            >
              {simulating && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              <span>Run Simulation</span>
            </button>
          </div>

          <div className="p-5 rounded-2xl bg-red-950/20 border border-red-900/60 flex flex-col justify-between space-y-4">
            <div className="space-y-1.5">
              <div className="flex items-center gap-2 font-bold text-sm text-red-300">
                <Flame className="w-4 h-4 text-red-400" />
                <span>{t('panicWipeBtn')}</span>
              </div>
              <p className="text-xs text-gray-400 leading-relaxed">
                {t('panicWipeDesc')}
              </p>
            </div>
            <button
              onClick={() => setShowPanicModal(true)}
              className="px-4 py-2 rounded-xl text-xs font-extrabold text-white bg-red-600 hover:bg-red-500 flex items-center justify-center gap-2 shadow-lg shadow-red-600/30 transition active:scale-95"
            >
              <span>{t('panicWipeBtn')}</span>
            </button>
          </div>
        </div>
      </div>

      <SimulateModal
        isOpen={showSimulateModal}
        plan={simulationPlan}
        onClose={() => setShowSimulateModal(false)}
      />

      <PanicModal
        isOpen={showPanicModal}
        onClose={() => setShowPanicModal(false)}
      />
    </div>
  );
};
