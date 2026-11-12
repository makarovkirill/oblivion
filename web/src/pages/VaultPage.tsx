import React, { useState } from 'react';
import {
  Plus,
  Trash2,
  Download,
  Key,
  FolderX,
  FileText,
  Lock,
  AlertOctagon,
  Paperclip,
  Loader2,
  X,
  Eye,
  EyeOff,
  Package
} from 'lucide-react';
import { useLanguage } from '../locales/LanguageContext';
import { VaultItem, TrustedContact, VaultPolicy, VaultCategory } from '../types';
import { api } from '../api';

interface VaultPageProps {
  items: VaultItem[];
  contacts: TrustedContact[];
  isUnlocked: boolean;
  onRefresh: () => void;
  onOpenUnlock: () => void;
}

export const VaultPage: React.FC<VaultPageProps> = ({
  items,
  contacts,
  isUnlocked,
  onRefresh,
  onOpenUnlock,
}) => {
  const { t } = useLanguage();
  const [showAddModal, setShowAddModal] = useState(false);
  const [revealedIds, setRevealedIds] = useState<Record<string, boolean>>({});

  const [title, setTitle] = useState('');
  const [category, setCategory] = useState<VaultCategory>('note');
  const [content, setContent] = useState('');
  const [policy, setPolicy] = useState<VaultPolicy>('transfer_and_wipe');
  const [targetPath, setTargetPath] = useState('');
  const [selectedContacts, setSelectedContacts] = useState<string[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleReveal = (id: string) => {
    setRevealedIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title) return;

    setSaving(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('title', title);
      formData.append('category', category);
      formData.append('content', content);
      formData.append('policy', policy);
      if (targetPath) formData.append('target_path', targetPath);
      formData.append('contact_ids', JSON.stringify(selectedContacts));
      if (file) formData.append('file', file);

      await api.createVaultItem(formData);
      setShowAddModal(false);
      resetForm();
      onRefresh();
    } catch (err: any) {
      setError(err.message || 'Failed to create item');
    } finally {
      setSaving(false);
    }
  };

  const resetForm = () => {
    setTitle('');
    setCategory('note');
    setContent('');
    setPolicy('transfer_and_wipe');
    setTargetPath('');
    setSelectedContacts([]);
    setFile(null);
    setError(null);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Permanently delete this vault item?')) return;
    try {
      await api.deleteVaultItem(id);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Failed to delete item');
    }
  };

  const getContactNames = (cids: string[]) => {
    return cids
      .map((id) => contacts.find((c) => c.id === id)?.name)
      .filter(Boolean)
      .join(', ');
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-gray-100">{t('navVault')}</h2>
          <p className="text-xs text-gray-400">Zero-knowledge storage, split-key assignments, and physical disk shredding targets.</p>
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
          <span>{t('addItemBtn')}</span>
        </button>
      </div>

      {!isUnlocked && (
        <div className="p-4 rounded-2xl bg-amber-950/20 border border-amber-800/40 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Lock className="w-5 h-5 text-amber-400 flex-shrink-0" />
            <p className="text-xs text-amber-200">
              Vault session is currently locked. Master password is required to decrypt entries, view plaintext payloads, or add new items.
            </p>
          </div>
          <button
            onClick={onOpenUnlock}
            className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-amber-500 text-gray-950 hover:bg-amber-400 transition flex-shrink-0"
          >
            {t('unlockVault')}
          </button>
        </div>
      )}

      {items.length === 0 ? (
        <div className="p-12 text-center bg-surface border border-border rounded-2xl">
          <FolderX className="w-10 h-10 text-gray-600 mx-auto mb-3" />
          <p className="text-xs text-gray-400">{t('vaultEmpty')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {items.map((item) => {
            const isRevealed = revealedIds[item.id] || false;
            return (
              <div
                key={item.id}
                className="p-5 rounded-2xl bg-surface border border-border hover:border-gray-700 transition space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-xl bg-card border border-border text-gray-300">
                      {item.category === 'credential' && <Key className="w-4 h-4 text-amber-400" />}
                      {item.category === 'file' && <Paperclip className="w-4 h-4 text-blue-400" />}
                      {item.category === 'target_path' && <AlertOctagon className="w-4 h-4 text-red-400" />}
                      {item.category === 'note' && <FileText className="w-4 h-4 text-emerald-400" />}
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-gray-100">{item.title}</h4>
                      <div className="flex flex-wrap items-center gap-2 mt-1">
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                            item.policy === 'transfer_and_wipe'
                              ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                              : 'bg-red-500/10 text-red-400 border border-red-500/20'
                          }`}
                        >
                          {item.policy === 'transfer_and_wipe'
                            ? t('policyTransferWipe')
                            : t('policyWipeOnly')}
                        </span>
                        {item.contact_ids.length > 0 && (
                          <span className="text-[10px] text-gray-400 bg-card px-2 py-0.5 rounded border border-border">
                            {getContactNames(item.contact_ids)}
                          </span>
                        )}
                        {item.attachment_filename && (
                          <span className="text-[10px] text-gray-400 flex items-center gap-1">
                            <Paperclip className="w-3 h-3" />
                            {item.attachment_filename}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-auto">
                    {item.content && (
                      <button
                        onClick={() => toggleReveal(item.id)}
                        className="p-2 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-card transition"
                        title="Toggle Content"
                      >
                        {isRevealed ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    )}
                    {isUnlocked && (
                      <a
                        href={`/api/vault/items/${item.id}/bundle`}
                        className="p-2 rounded-lg text-gray-400 hover:text-emerald-400 hover:bg-card transition"
                        title={t('downloadBundle')}
                      >
                        <Package className="w-4 h-4" />
                      </a>
                    )}
                    {item.has_attachment && isUnlocked && (
                      <a
                        href={`/api/vault/items/${item.id}/attachment`}
                        className="p-2 rounded-lg text-gray-400 hover:text-blue-400 hover:bg-card transition"
                        title={t('downloadAttachment')}
                      >
                        <Download className="w-4 h-4" />
                      </a>
                    )}
                    {isUnlocked && (
                      <button
                        onClick={() => handleDelete(item.id)}
                        className="p-2 rounded-lg text-gray-400 hover:text-red-400 hover:bg-card transition"
                        title={t('deleteItem')}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>

                {item.target_path && (
                  <div className="p-2.5 rounded-xl bg-card border border-border text-xs font-mono text-gray-400 flex items-center gap-2">
                    <span className="text-red-400 font-bold uppercase text-[10px]">Disk Target:</span>
                    <span className="truncate">{item.target_path}</span>
                  </div>
                )}

                {item.content && isRevealed && (
                  <div className="p-3 rounded-xl bg-black/40 border border-border/80 text-xs font-mono text-gray-200 whitespace-pre-wrap break-all">
                    {item.content}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div className="bg-surface border border-border rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl max-h-[90vh] flex flex-col">
            <div className="p-5 border-b border-border flex items-center justify-between">
              <h3 className="font-bold text-gray-100">{t('addItemBtn')}</h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-card transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreate} className="p-5 space-y-4 overflow-y-auto">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">{t('itemTitle')}</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Master Wallet Seed Phrase"
                  required
                  className="w-full px-3 py-2 rounded-xl bg-card border border-border text-gray-100 text-xs focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1">{t('itemCategory')}</label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value as VaultCategory)}
                    className="w-full px-3 py-2 rounded-xl bg-card border border-border text-gray-100 text-xs focus:outline-none focus:border-blue-500"
                  >
                    <option value="note">{t('catNote')}</option>
                    <option value="credential">{t('catCredential')}</option>
                    <option value="file">{t('catFile')}</option>
                    <option value="target_path">{t('catPath')}</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1">{t('itemPolicy')}</label>
                  <select
                    value={policy}
                    onChange={(e) => setPolicy(e.target.value as VaultPolicy)}
                    className="w-full px-3 py-2 rounded-xl bg-card border border-border text-gray-100 text-xs focus:outline-none focus:border-blue-500 font-semibold"
                  >
                    <option value="transfer_and_wipe">{t('policyTransferWipe')}</option>
                    <option value="wipe_only">{t('policyWipeOnly')}</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">{t('contentLabel')}</label>
                <textarea
                  rows={3}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="Secret payload..."
                  className="w-full px-3 py-2 rounded-xl bg-card border border-border text-gray-100 text-xs font-mono focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">{t('targetPathLabel')}</label>
                <input
                  type="text"
                  value={targetPath}
                  onChange={(e) => setTargetPath(e.target.value)}
                  placeholder={t('targetPathPlaceholder')}
                  className="w-full px-3 py-2 rounded-xl bg-card border border-border text-gray-100 text-xs font-mono focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">{t('attachmentLabel')}</label>
                <input
                  type="file"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="w-full text-xs text-gray-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-gray-800 file:text-gray-200 hover:file:bg-gray-700"
                />
              </div>

              {policy === 'transfer_and_wipe' && contacts.length > 0 && (
                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1.5">{t('itemContacts')}</label>
                  <div className="space-y-1.5 max-h-32 overflow-y-auto p-2 rounded-xl bg-card border border-border">
                    {contacts.map((c) => (
                      <label key={c.id} className="flex items-center gap-2 text-xs text-gray-300 hover:text-white cursor-pointer">
                        <input
                          type="checkbox"
                          checked={selectedContacts.includes(c.id)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedContacts([...selectedContacts, c.id]);
                            } else {
                              setSelectedContacts(selectedContacts.filter((id) => id !== c.id));
                            }
                          }}
                          className="rounded bg-surface border-border text-blue-600 focus:ring-0"
                        />
                        <span>{c.name} {c.email ? `(${c.email})` : ''}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              {error && (
                <div className="p-3 rounded-xl bg-red-950/40 border border-red-800 text-red-300 text-xs">
                  {error}
                </div>
              )}

              <div className="pt-3 border-t border-border flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-gray-300 hover:text-white rounded-xl transition"
                >
                  {t('cancelBtn')}
                </button>
                <button
                  type="submit"
                  disabled={saving || !title}
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
