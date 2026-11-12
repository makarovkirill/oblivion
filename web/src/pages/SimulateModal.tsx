import React from 'react';
import { X, PlayCircle, Send, Trash2, Database, CheckCircle2 } from 'lucide-react';
import { useLanguage } from '../locales/LanguageContext';

interface SimulateModalProps {
  isOpen: boolean;
  plan: any;
  onClose: () => void;
}

export const SimulateModal: React.FC<SimulateModalProps> = ({ isOpen, plan, onClose }) => {
  const { t } = useLanguage();

  if (!isOpen || !plan) return null;

  const transfers = plan.transfers || [];
  const wipes = plan.wipes || [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
      <div className="bg-surface border border-border rounded-3xl w-full max-w-2xl overflow-hidden shadow-2xl max-h-[85vh] flex flex-col">
        <div className="p-5 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-blue-600/10 text-blue-400 border border-blue-500/20">
              <PlayCircle className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-gray-100 text-sm">{t('simulationModalTitle')}</h3>
              <p className="text-[11px] text-gray-400 font-mono">OBLIVION TRIGGER SIMULATION</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg text-gray-400 hover:text-white transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6 overflow-y-auto">
          <div className="p-3.5 rounded-xl bg-blue-950/20 border border-blue-800/40 text-xs text-blue-300 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-blue-400 flex-shrink-0" />
            <span>Simulation executed safely. No live secrets were transmitted and no files were shredded.</span>
          </div>

          <div>
            <div className="flex items-center gap-2 text-xs font-bold text-gray-200 mb-2">
              <Send className="w-4 h-4 text-blue-400" />
              <span>{t('simulationTransfers')} ({transfers.length})</span>
            </div>

            {transfers.length === 0 ? (
              <p className="text-xs text-gray-500 italic p-3 rounded-xl bg-card border border-border">No items marked for Transfer & Wipe.</p>
            ) : (
              <div className="space-y-2">
                {transfers.map((item: any, idx: number) => (
                  <div key={idx} className="p-3 rounded-xl bg-card border border-border text-xs space-y-1.5">
                    <div className="flex items-center justify-between font-semibold text-gray-100">
                      <span>{item.title}</span>
                      <span className="text-[10px] font-mono text-emerald-400">
                        {item.bundle_file}
                      </span>
                    </div>
                    {item.recipients?.length > 0 && (
                      <div className="text-[11px] text-gray-400 flex flex-wrap gap-2">
                        {item.recipients.map((r: any, rIdx: number) => (
                          <span key={rIdx} className="bg-surface px-2 py-0.5 rounded border border-border">
                            {r.name} {r.telegram ? '(TG)' : ''} {r.email ? '(Email)' : ''}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            <div className="flex items-center gap-2 text-xs font-bold text-gray-200 mb-2">
              <Trash2 className="w-4 h-4 text-red-400" />
              <span>{t('simulationWipes')} ({wipes.length + 1})</span>
            </div>

            <div className="space-y-2">
              <div className="p-3 rounded-xl bg-red-950/20 border border-red-900/40 text-xs flex items-center justify-between font-mono">
                <div className="flex items-center gap-2 text-red-300 truncate">
                  <Database className="w-4 h-4 flex-shrink-0 text-red-400" />
                  <span className="truncate">{plan.database_target}</span>
                </div>
                <span className="text-[10px] font-bold text-red-400 uppercase">Oblivion DB Wipe</span>
              </div>

              {wipes.map((w: any, idx: number) => (
                <div key={idx} className="p-3 rounded-xl bg-card border border-border text-xs flex items-center justify-between font-mono">
                  <span className="truncate text-gray-300 max-w-sm">{w.path}</span>
                  <span className="text-[10px] text-gray-500">{w.reason}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="p-4 border-t border-border flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-blue-600 hover:bg-blue-500 transition"
          >
            {t('closeBtn')}
          </button>
        </div>
      </div>
    </div>
  );
};
