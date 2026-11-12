import React, { useState } from 'react';
import {
  ShieldAlert,
  Send,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  Loader2,
  Mail,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { useLanguage } from '../locales/LanguageContext';
import { api } from '../api';

interface SetupWizardPageProps {
  onSetupCompleted: () => void;
}

export const SetupWizardPage: React.FC<SetupWizardPageProps> = ({ onSetupCompleted }) => {
  const { language, setLanguage, t } = useLanguage();
  const [step, setStep] = useState(1);

  const [masterPassword, setMasterPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [checkinPassphrase, setCheckinPassphrase] = useState('');
  const [uninstallKey, setUninstallKey] = useState('1234');

  const [telegramToken, setTelegramToken] = useState('');
  const [telegramChatId, setTelegramChatId] = useState('');
  const [testPingLoading, setTestPingLoading] = useState(false);
  const [testPingResult, setTestPingResult] = useState<{ success: boolean; msg: string } | null>(null);

  const [showSmtp, setShowSmtp] = useState(false);
  const [smtpHost, setSmtpHost] = useState('');
  const [smtpPort, setSmtpPort] = useState(587);
  const [smtpUser, setSmtpUser] = useState('');
  const [smtpPassword, setSmtpPassword] = useState('');
  const [smtpFrom, setSmtpFrom] = useState('');
  const [testEmailLoading, setTestEmailLoading] = useState(false);
  const [testEmailResult, setTestEmailResult] = useState<{ success: boolean; msg: string } | null>(null);

  const [intervalSeconds, setIntervalSeconds] = useState(604800);
  const [graceSeconds, setGraceSeconds] = useState(86400);

  const [initLoading, setInitLoading] = useState(false);
  const [initError, setInitError] = useState<string | null>(null);

  const calculateStrength = (pass: string) => {
    let score = 0;
    if (pass.length >= 8) score++;
    if (pass.length >= 16) score++;
    if (/[A-Z]/.test(pass) && /[a-z]/.test(pass)) score++;
    if (/\d/.test(pass)) score++;
    if (/[^A-Za-z0-9]/.test(pass)) score++;
    return score;
  };

  const passphraseStrength = calculateStrength(checkinPassphrase);

  const handleTestPing = async () => {
    if (!telegramToken || !telegramChatId) return;
    setTestPingLoading(true);
    setTestPingResult(null);
    try {
      const res = await api.testTelegram(telegramToken, telegramChatId);
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
        password: smtpPassword,
        from_addr: smtpFrom,
        target_email: smtpFrom,
        use_tls: true,
      });
      setTestEmailResult({ success: true, msg: res.message || 'Email test successful' });
    } catch (err: any) {
      setTestEmailResult({ success: false, msg: err.message || 'SMTP test failed' });
    } finally {
      setTestEmailLoading(false);
    }
  };

  const handleFinishSetup = async () => {
    setInitLoading(true);
    setInitError(null);
    try {
      await api.initializeSystem({
        language,
        master_password: masterPassword,
        checkin_passphrase: checkinPassphrase,
        uninstall_key: uninstallKey.trim() || '1234',
        telegram_token: telegramToken.trim() || null,
        telegram_chat_id: telegramChatId.trim() || null,
        smtp_host: smtpHost.trim() || null,
        smtp_port: smtpPort,
        smtp_user: smtpUser.trim() || null,
        smtp_password: smtpPassword || null,
        smtp_from: smtpFrom.trim() || null,
        smtp_use_tls: true,
        interval_seconds: intervalSeconds,
        grace_seconds: graceSeconds,
      });
      onSetupCompleted();
    } catch (err: any) {
      setInitError(err.message || 'Initialization failed');
    } finally {
      setInitLoading(false);
    }
  };

  const canProceedStep2 =
    masterPassword.length >= 8 &&
    masterPassword === confirmPassword &&
    checkinPassphrase.length >= 16 &&
    uninstallKey.trim().length >= 4;

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-2xl bg-surface border border-border rounded-3xl p-6 sm:p-8 shadow-2xl">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2.5 rounded-xl bg-blue-600/10 text-blue-400 border border-blue-500/20">
            <ShieldAlert className="w-7 h-7" />
          </div>
          <div>
            <h2 className="text-xl font-black text-gray-100 tracking-wider">OBLIVION</h2>
            <p className="text-xs text-gray-400 font-mono">{t('wizardTitle')}</p>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-2 mb-8">
          {[1, 2, 3, 4].map((s) => (
            <div key={s} className="flex flex-col gap-1.5">
              <div
                className={`h-1.5 rounded-full transition-all duration-300 ${
                  s === step
                    ? 'bg-blue-500'
                    : s < step
                    ? 'bg-emerald-500'
                    : 'bg-gray-800'
                }`}
              />
              <span className={`text-[10px] font-medium tracking-wide uppercase ${
                s === step ? 'text-blue-400' : s < step ? 'text-emerald-400' : 'text-gray-600'
              }`}>
                {s === 1 && t('wizardStep1')}
                {s === 2 && t('wizardStep2')}
                {s === 3 && t('wizardStep3')}
                {s === 4 && t('wizardStep4')}
              </span>
            </div>
          ))}
        </div>

        {step === 1 && (
          <div className="space-y-6 animate-in fade-in">
            <div>
              <h3 className="text-base font-bold text-gray-100 mb-1">{t('languageSelectLabel')}</h3>
              <p className="text-xs text-gray-400">Choose the language for OBLIVION dashboards, alerts, and Telegram bots.</p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <button
                type="button"
                onClick={() => setLanguage('en')}
                className={`p-6 rounded-2xl border text-left flex flex-col gap-2 transition ${
                  language === 'en'
                    ? 'bg-blue-600/10 border-blue-500 text-blue-400 ring-2 ring-blue-500/20'
                    : 'bg-card border-border text-gray-300 hover:border-gray-600'
                }`}
              >
                <span className="text-2xl font-bold font-mono">English</span>
                <span className="text-xs text-gray-400">Complete English interface and alerts</span>
              </button>

              <button
                type="button"
                onClick={() => setLanguage('ru')}
                className={`p-6 rounded-2xl border text-left flex flex-col gap-2 transition ${
                  language === 'ru'
                    ? 'bg-blue-600/10 border-blue-500 text-blue-400 ring-2 ring-blue-500/20'
                    : 'bg-card border-border text-gray-300 hover:border-gray-600'
                }`}
              >
                <span className="text-2xl font-bold font-mono">Русский</span>
                <span className="text-xs text-gray-400">OBLIVION — русскоязычная локализация и бот</span>
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-5 animate-in fade-in">
            <div>
              <h3 className="text-base font-bold text-gray-100 mb-1">{t('wizardStep2')}</h3>
              <p className="text-xs text-gray-400">Set the vault encryption password and your activity check-in passphrase.</p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">
                  {t('masterPasswordLabel')}
                </label>
                <input
                  type="password"
                  value={masterPassword}
                  onChange={(e) => setMasterPassword(e.target.value)}
                  placeholder="Min 8 characters..."
                  className="w-full px-3.5 py-2.5 rounded-xl bg-card border border-border text-gray-100 text-sm focus:outline-none focus:border-blue-500"
                />
                <p className="text-[11px] text-gray-500 mt-1">{t('masterPasswordHint')}</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">
                  {t('confirmPasswordLabel')}
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter master password..."
                  className="w-full px-3.5 py-2.5 rounded-xl bg-card border border-border text-gray-100 text-sm focus:outline-none focus:border-blue-500"
                />
                {confirmPassword && masterPassword !== confirmPassword && (
                  <p className="text-[11px] text-red-400 mt-1">{t('passwordMismatch')}</p>
                )}
              </div>

              <div className="pt-2 border-t border-border/60">
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-semibold text-gray-300">
                    {t('checkInPassphraseLabel')}
                  </label>
                  <span className={`text-[11px] font-mono font-medium ${
                    checkinPassphrase.length >= 16 ? 'text-emerald-400' : 'text-amber-400'
                  }`}>
                    {checkinPassphrase.length} / 16 {checkinPassphrase.length >= 16 ? '✓' : `(${16 - checkinPassphrase.length} more)`}
                  </span>
                </div>
                <input
                  type="password"
                  value={checkinPassphrase}
                  onChange={(e) => setCheckinPassphrase(e.target.value)}
                  placeholder="Strictly 16+ characters passphrase..."
                  className="w-full px-3.5 py-2.5 rounded-xl bg-card border border-border text-gray-100 text-sm focus:outline-none focus:border-blue-500 font-mono"
                />
                <p className="text-[11px] text-gray-500 mt-1">{t('checkInPassphraseHint')}</p>

                <div className="mt-2 flex items-center gap-2">
                  <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden flex gap-0.5">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <div
                        key={i}
                        className={`flex-1 h-full transition ${
                          passphraseStrength >= i
                            ? passphraseStrength <= 2
                              ? 'bg-amber-500'
                              : passphraseStrength <= 3
                              ? 'bg-blue-500'
                              : 'bg-emerald-500'
                            : 'bg-transparent'
                        }`}
                      />
                    ))}
                  </div>
                  <span className="text-[10px] text-gray-400 font-medium">
                    {passphraseStrength <= 2 ? t('strengthWeak') : passphraseStrength <= 3 ? t('strengthFair') : t('strengthStrong')}
                  </span>
                </div>
              </div>

              <div className="pt-2 border-t border-border/60">
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-semibold text-gray-300">
                    {t('uninstallKeyLabel')}
                  </label>
                  <span className={`text-[11px] font-mono font-medium ${
                    uninstallKey.length >= 4 ? 'text-emerald-400' : 'text-amber-400'
                  }`}>
                    {uninstallKey.length} / 4 {uninstallKey.length >= 4 ? '✓' : `(${4 - uninstallKey.length} more)`}
                  </span>
                </div>
                <input
                  type="text"
                  value={uninstallKey}
                  onChange={(e) => setUninstallKey(e.target.value)}
                  placeholder={t('uninstallKeyPlaceholder')}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-card border border-border text-gray-100 text-sm focus:outline-none focus:border-blue-500 font-mono"
                />
                <p className="text-[11px] text-gray-500 mt-1">{t('uninstallKeyHint')}</p>
              </div>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-5 animate-in fade-in">
            <div>
              <h3 className="text-base font-bold text-gray-100 mb-1">{t('telegramSetupTitle')}</h3>
              <p className="text-xs text-gray-400">{t('telegramSetupDesc')}</p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">
                  {t('botTokenLabel')}
                </label>
                <input
                  type="text"
                  value={telegramToken}
                  onChange={(e) => setTelegramToken(e.target.value)}
                  placeholder={t('botTokenPlaceholder')}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-card border border-border text-gray-100 text-sm focus:outline-none focus:border-blue-500 font-mono"
                />
                <div className="mt-2 p-3 rounded-xl bg-blue-950/20 border border-blue-800/40 text-[11px] text-blue-300 whitespace-pre-line">
                  {t('botTokenGuide')}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">
                  {t('ownerChatIdLabel')}
                </label>
                <input
                  type="text"
                  value={telegramChatId}
                  onChange={(e) => setTelegramChatId(e.target.value)}
                  placeholder={t('ownerChatIdPlaceholder')}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-card border border-border text-gray-100 text-sm focus:outline-none focus:border-blue-500 font-mono"
                />
                <p className="text-[11px] text-gray-500 mt-1">{t('ownerChatIdGuide')}</p>
              </div>

              {telegramToken && telegramChatId && (
                <div className="flex items-center gap-3 pt-1">
                  <button
                    type="button"
                    onClick={handleTestPing}
                    disabled={testPingLoading}
                    className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-sky-600 hover:bg-sky-500 flex items-center gap-2 shadow-lg transition active:scale-95 disabled:opacity-50"
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

              <div className="pt-2 border-t border-border/60">
                <button
                  type="button"
                  onClick={() => setShowSmtp(!showSmtp)}
                  className="text-xs text-gray-400 hover:text-gray-200 flex items-center gap-1.5 transition"
                >
                  <Mail className="w-3.5 h-3.5" />
                  <span>{t('optionalSmtpTitle')}</span>
                  {showSmtp ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>

                {showSmtp && (
                  <div className="mt-3 p-4 rounded-xl bg-card border border-border space-y-3 animate-in fade-in">
                    <div className="grid grid-cols-3 gap-3">
                      <div className="col-span-2">
                        <label className="text-[11px] text-gray-400 block mb-1">{t('smtpHostLabel')}</label>
                        <input
                          type="text"
                          value={smtpHost}
                          onChange={(e) => setSmtpHost(e.target.value)}
                          placeholder="smtp.gmail.com"
                          className="w-full px-3 py-1.5 rounded-lg bg-surface border border-border text-xs text-gray-100"
                        />
                      </div>
                      <div>
                        <label className="text-[11px] text-gray-400 block mb-1">{t('smtpPortLabel')}</label>
                        <input
                          type="number"
                          value={smtpPort}
                          onChange={(e) => setSmtpPort(Number(e.target.value))}
                          className="w-full px-3 py-1.5 rounded-lg bg-surface border border-border text-xs text-gray-100 font-mono"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-[11px] text-gray-400 block mb-1">{t('smtpUserLabel')}</label>
                        <input
                          type="text"
                          value={smtpUser}
                          onChange={(e) => setSmtpUser(e.target.value)}
                          className="w-full px-3 py-1.5 rounded-lg bg-surface border border-border text-xs text-gray-100"
                        />
                      </div>
                      <div>
                        <label className="text-[11px] text-gray-400 block mb-1">{t('smtpPassLabel')}</label>
                        <input
                          type="password"
                          value={smtpPassword}
                          onChange={(e) => setSmtpPassword(e.target.value)}
                          className="w-full px-3 py-1.5 rounded-lg bg-surface border border-border text-xs text-gray-100"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="text-[11px] text-gray-400 block mb-1">{t('smtpFromLabel')}</label>
                      <input
                        type="text"
                        value={smtpFrom}
                        onChange={(e) => setSmtpFrom(e.target.value)}
                        placeholder="alerts@domain.com"
                        className="w-full px-3 py-1.5 rounded-lg bg-surface border border-border text-xs text-gray-100"
                      />
                    </div>

                    {smtpHost && smtpFrom && (
                      <div className="pt-2 flex items-center gap-3">
                        <button
                          type="button"
                          onClick={handleTestEmail}
                          disabled={testEmailLoading}
                          className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-gray-700 hover:bg-gray-600 text-gray-200 flex items-center gap-1.5 transition"
                        >
                          {testEmailLoading && <Loader2 className="w-3 h-3 animate-spin" />}
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
                )}
              </div>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-6 animate-in fade-in">
            <div>
              <h3 className="text-base font-bold text-gray-100 mb-1">{t('timerSetupTitle')}</h3>
              <p className="text-xs text-gray-400">{t('timerSetupDesc')}</p>
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
                      onClick={() => setIntervalSeconds(p.sec)}
                      className={`p-3 rounded-xl border text-left text-xs font-medium transition ${
                        intervalSeconds === p.sec
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
                      onClick={() => setGraceSeconds(p.sec)}
                      className={`p-3 rounded-xl border text-left text-xs font-medium transition ${
                        graceSeconds === p.sec
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

            {initError && (
              <div className="p-3 rounded-xl bg-red-950/40 border border-red-800 text-red-300 text-xs">
                {initError}
              </div>
            )}
          </div>
        )}

        <div className="mt-8 pt-5 border-t border-border flex items-center justify-between">
          {step > 1 ? (
            <button
              type="button"
              onClick={() => setStep(step - 1)}
              className="px-4 py-2 text-xs font-semibold text-gray-300 hover:text-white rounded-xl flex items-center gap-1.5 transition"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>{t('backBtn')}</span>
            </button>
          ) : <div />}

          {step < 4 ? (
            <button
              type="button"
              onClick={() => setStep(step + 1)}
              disabled={step === 2 && !canProceedStep2}
              className="px-6 py-2.5 rounded-xl text-xs font-bold text-white bg-blue-600 hover:bg-blue-500 flex items-center gap-1.5 shadow-lg transition active:scale-95 disabled:opacity-50"
            >
              <span>{t('nextBtn')}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleFinishSetup}
              disabled={initLoading}
              className="px-6 py-2.5 rounded-xl text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-500 flex items-center gap-2 shadow-lg transition active:scale-95 disabled:opacity-50"
            >
              {initLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
              <span>{t('finishBtn')}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
