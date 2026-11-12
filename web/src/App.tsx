import React, { useState, useEffect } from 'react';
import { LayoutDashboard, Database, Users, Settings, Loader2 } from 'lucide-react';
import { useLanguage } from './locales/LanguageContext';
import { SystemStatusResponse, VaultItem, TrustedContact, AuditLog } from './types';
import { api } from './api';
import { Header } from './components/Header';
import { OverviewPage } from './pages/OverviewPage';
import { VaultPage } from './pages/VaultPage';
import { ContactsPage } from './pages/ContactsPage';
import { SettingsPage } from './pages/SettingsPage';
import { SetupWizardPage } from './pages/SetupWizardPage';
import { CheckInModal } from './components/CheckInModal';
import { UnlockModal } from './components/UnlockModal';

export const App: React.FC = () => {
  const { t, setLanguage } = useLanguage();
  const [loading, setLoading] = useState(true);
  const [setupCompleted, setSetupCompleted] = useState<boolean | null>(null);

  const [statusData, setStatusData] = useState<SystemStatusResponse | null>(null);
  const [vaultItems, setVaultItems] = useState<VaultItem[]>([]);
  const [contacts, setContacts] = useState<TrustedContact[]>([]);
  const [logs, setLogs] = useState<AuditLog[]>([]);

  const [activeTab, setActiveTab] = useState<'overview' | 'vault' | 'contacts' | 'settings'>('overview');
  const [showCheckInModal, setShowCheckInModal] = useState(false);
  const [showUnlockModal, setShowUnlockModal] = useState(false);

  useEffect(() => {
    checkInitialState();
  }, []);

  useEffect(() => {
    if (setupCompleted) {
      const interval = setInterval(() => {
        refreshStatus();
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [setupCompleted]);

  const checkInitialState = async () => {
    setLoading(true);
    try {
      const setupRes = await api.getSetupStatus();
      setSetupCompleted(setupRes.setup_completed);
      if (setupRes.language) {
        setLanguage(setupRes.language as any);
      }

      if (setupRes.setup_completed) {
        await refreshAllData();
      }
    } catch (err: any) {
      console.error('Initial state check error:', err);
    } finally {
      setLoading(false);
    }
  };

  const refreshStatus = async () => {
    try {
      const res = await api.getStatus();
      setStatusData(res);
    } catch (err: any) {
      console.error('Failed to refresh status:', err);
    }
  };

  const refreshAllData = async () => {
    try {
      const [statusRes, vaultRes, contactsRes, logsRes] = await Promise.all([
        api.getStatus(),
        api.getVaultItems(),
        api.getContacts(),
        api.getLogs(50),
      ]);
      setStatusData(statusRes);
      setVaultItems(vaultRes.items || []);
      setContacts(contactsRes.contacts || []);
      setLogs(logsRes.logs || []);
    } catch (err: any) {
      console.error('Failed to refresh data:', err);
    }
  };

  const handleLockVault = async () => {
    try {
      await api.lockVault();
      refreshAllData();
    } catch (err: any) {
      alert(err.message || 'Failed to lock vault');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
          <span className="text-xs text-gray-400 font-mono">Initializing OBLIVION...</span>
        </div>
      </div>
    );
  }

  if (setupCompleted === false) {
    return (
      <SetupWizardPage
        onSetupCompleted={() => {
          setSetupCompleted(true);
          refreshAllData();
        }}
      />
    );
  }

  const isUnlocked = statusData?.switch.unlocked_session ?? false;

  return (
    <div className="min-h-screen bg-background text-gray-100 flex flex-col font-sans">
      <Header
        statusData={statusData}
        onOpenUnlock={() => setShowUnlockModal(true)}
        onLockVault={handleLockVault}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        <nav className="flex space-x-1 rounded-2xl bg-surface p-1.5 border border-border">
          {[
            { id: 'overview', label: t('navOverview'), icon: LayoutDashboard },
            { id: 'vault', label: t('navVault'), icon: Database },
            { id: 'contacts', label: t('navContacts'), icon: Users },
            { id: 'settings', label: t('navSettings'), icon: Settings },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl text-xs font-bold transition ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-card/50'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>

        {activeTab === 'overview' && statusData && (
          <OverviewPage
            switchData={statusData.switch}
            windowsData={statusData.windows}
            vaultCount={vaultItems.length}
            contactsCount={contacts.length}
            logs={logs}
            onOpenCheckIn={() => setShowCheckInModal(true)}
          />
        )}

        {activeTab === 'vault' && (
          <VaultPage
            items={vaultItems}
            contacts={contacts}
            isUnlocked={isUnlocked}
            onRefresh={refreshAllData}
            onOpenUnlock={() => setShowUnlockModal(true)}
          />
        )}

        {activeTab === 'contacts' && (
          <ContactsPage
            contacts={contacts}
            isUnlocked={isUnlocked}
            onRefresh={refreshAllData}
            onOpenUnlock={() => setShowUnlockModal(true)}
          />
        )}

        {activeTab === 'settings' && (
          <SettingsPage
            isUnlocked={isUnlocked}
            onOpenUnlock={() => setShowUnlockModal(true)}
            onRefreshStatus={refreshAllData}
          />
        )}
      </main>

      <CheckInModal
        isOpen={showCheckInModal}
        onClose={() => setShowCheckInModal(false)}
        onSuccess={() => {
          refreshAllData();
        }}
      />

      <UnlockModal
        isOpen={showUnlockModal}
        onClose={() => setShowUnlockModal(false)}
        onSuccess={() => {
          refreshAllData();
        }}
      />
    </div>
  );
};
