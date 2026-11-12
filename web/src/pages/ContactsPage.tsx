import React, { useState } from 'react';
import { Plus, Trash2, UserCheck, KeyRound, Copy, Check, MessageSquare, Mail, X, Loader2 } from 'lucide-react';
import { useLanguage } from '../locales/LanguageContext';
import { TrustedContact } from '../types';
import { api } from '../api';

interface ContactsPageProps {
  contacts: TrustedContact[];
  isUnlocked: boolean;
  onRefresh: () => void;
  onOpenUnlock: () => void;
}

export const ContactsPage: React.FC<ContactsPageProps> = ({
  contacts,
  isUnlocked,
  onRefresh,
  onOpenUnlock,
}) => {
  const { t } = useLanguage();
  const [showAddModal, setShowAddModal] = useState(false);
  const [copiedToken, setCopiedToken] = useState<string | null>(null);

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [telegramChatId, setTelegramChatId] = useState('');
  const [publicInstructions, setPublicInstructions] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [newlyCreatedToken, setNewlyCreatedToken] = useState<{ name: string; token: string } | null>(null);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name) return;

    setSaving(true);
    setError(null);

    try {
      const res = await api.createContact({
        name,
        email: email.trim() || null,
        telegram_chat_id: telegramChatId.trim() || null,
        public_instructions: publicInstructions.trim() || null,
      });

      setNewlyCreatedToken({ name, token: res.recovery_token });
      setShowAddModal(false);
      setName('');
      setEmail('');
      setTelegramChatId('');
      setPublicInstructions('');
      onRefresh();
    } catch (err: any) {
      setError(err.message || 'Failed to create contact');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this trusted contact?')) return;
    try {
      await api.deleteContact(id);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Failed to delete contact');
    }
  };

  const copyToClipboard = (token: string) => {
    navigator.clipboard.writeText(token);
    setCopiedToken(token);
    setTimeout(() => setCopiedToken(null), 2000);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-gray-100">{t('contactsTitle')}</h2>
          <p className="text-xs text-gray-400">{t('contactsDesc')}</p>
        </div>

        <button
          onClick={() => {
            if (!isUnlocked) {
              onOpenUnlock();
            } else {
              setShowAddModal(true);
            }
          }}
          className="px-4 py-2.5 rounded-xl text-xs font-bold text-white bg-blue-600 hover:bg-blue-500 flex items-center gap-2 shadow-lg transition active:scale-95 self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>{t('addContactBtn')}</span>
        </button>
      </div>

      {newlyCreatedToken && (
        <div className="p-5 rounded-2xl bg-emerald-950/30 border border-emerald-800/80 space-y-3 animate-in fade-in">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
              <KeyRound className="w-4 h-4" />
              <span>{t('recoveryTokenTitle')} for {newlyCreatedToken.name}</span>
            </div>
            <button
              onClick={() => setNewlyCreatedToken(null)}
              className="text-gray-400 hover:text-gray-200"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <p className="text-xs text-emerald-200 leading-relaxed">
            {t('recoveryTokenDesc')}
          </p>
          <div className="flex items-center gap-2 bg-black/60 p-2.5 rounded-xl border border-emerald-800/60 font-mono text-xs text-emerald-300">
            <span className="flex-1 break-all select-all">{newlyCreatedToken.token}</span>
            <button
              onClick={() => copyToClipboard(newlyCreatedToken.token)}
              className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-sans text-xs font-semibold flex items-center gap-1.5 transition flex-shrink-0"
            >
              {copiedToken === newlyCreatedToken.token ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedToken === newlyCreatedToken.token ? 'Copied' : t('copyToken')}</span>
            </button>
          </div>
        </div>
      )}

      {contacts.length === 0 ? (
        <div className="p-12 text-center bg-surface border border-border rounded-2xl">
          <UserCheck className="w-10 h-10 text-gray-600 mx-auto mb-3" />
          <p className="text-xs text-gray-400">No trusted contacts registered yet.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {contacts.map((c) => (
            <div
              key={c.id}
              className="p-5 rounded-2xl bg-surface border border-border hover:border-gray-700 transition flex flex-col justify-between space-y-4"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="font-bold text-sm text-gray-100">{c.name}</h4>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                    {c.assigned_items_count} Assigned Items
                  </span>
                </div>

                <div className="space-y-1 text-xs text-gray-400">
                  {c.email && (
                    <div className="flex items-center gap-2">
                      <Mail className="w-3.5 h-3.5 text-gray-500" />
                      <span>{c.email}</span>
                    </div>
                  )}
                  {c.telegram_chat_id && (
                    <div className="flex items-center gap-2 font-mono">
                      <MessageSquare className="w-3.5 h-3.5 text-sky-400" />
                      <span>TG: {c.telegram_chat_id}</span>
                    </div>
                  )}
                </div>

                {c.public_instructions && (
                  <div className="p-2.5 rounded-xl bg-card border border-border text-[11px] text-gray-400">
                    <span className="text-gray-300 font-semibold block mb-0.5">Instructions:</span>
                    <p className="line-clamp-2">{c.public_instructions}</p>
                  </div>
                )}
              </div>

              {isUnlocked && (
                <div className="pt-3 border-t border-border flex justify-end">
                  <button
                    onClick={() => handleDelete(c.id)}
                    className="p-1.5 rounded-lg text-gray-400 hover:text-red-400 hover:bg-card transition"
                    title="Delete contact"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div className="bg-surface border border-border rounded-2xl w-full max-w-md overflow-hidden shadow-2xl">
            <div className="p-5 border-b border-border flex items-center justify-between">
              <h3 className="font-bold text-gray-100">{t('addContactBtn')}</h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-card transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreate} className="p-5 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">{t('contactName')}</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Elena Rostova"
                  required
                  className="w-full px-3 py-2 rounded-xl bg-card border border-border text-gray-100 text-xs focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">{t('contactEmail')}</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="contact@example.com"
                  className="w-full px-3 py-2 rounded-xl bg-card border border-border text-gray-100 text-xs focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">{t('contactTelegram')}</label>
                <input
                  type="text"
                  value={telegramChatId}
                  onChange={(e) => setTelegramChatId(e.target.value)}
                  placeholder="e.g. 987654321"
                  className="w-full px-3 py-2 rounded-xl bg-card border border-border text-gray-100 text-xs font-mono focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">{t('instructionsLabel')}</label>
                <textarea
                  rows={2}
                  value={publicInstructions}
                  onChange={(e) => setPublicInstructions(e.target.value)}
                  placeholder="Guidance for recipient..."
                  className="w-full px-3 py-2 rounded-xl bg-card border border-border text-gray-100 text-xs focus:outline-none focus:border-blue-500"
                />
              </div>

              {error && (
                <div className="p-3 rounded-xl bg-red-950/40 border border-red-800 text-red-300 text-xs">
                  {error}
                </div>
              )}

              <div className="pt-2 border-t border-border flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-gray-300 hover:text-white rounded-xl transition"
                >
                  {t('cancelBtn')}
                </button>
                <button
                  type="submit"
                  disabled={saving || !name}
                  className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-blue-600 hover:bg-blue-500 flex items-center gap-2 shadow-lg transition active:scale-95 disabled:opacity-50"
                >
                  {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>{t('saveBtn')}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
