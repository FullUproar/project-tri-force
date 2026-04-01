"use client";

import { Upload, Sparkles, FileDown } from "lucide-react";

interface WelcomeHeroProps {
  onTryDemo: () => void;
  isDemoLoading: boolean;
}

export function WelcomeHero({ onTryDemo, isDemoLoading }: WelcomeHeroProps) {
  return (
    <div className="col-span-full p-8 bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-xl">
      <div className="max-w-2xl mx-auto text-center space-y-4">
        <h2 className="text-2xl font-bold text-gray-900">
          AI-Powered Prior Authorization
        </h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          Upload a surgeon's clinical note, robotic report, or DICOM file.
          CortaLoom extracts the diagnosis, failed treatments, and implant details,
          then generates a payer-ready narrative in seconds — not hours.
        </p>

        <div className="grid grid-cols-3 gap-4 pt-2">
          <div className="p-3 bg-white/70 rounded-lg">
            <Upload className="w-5 h-5 mx-auto mb-1 text-blue-600" />
            <p className="text-xs font-medium">1. Upload</p>
            <p className="text-xs text-gray-500">Clinical note, PDF, or DICOM</p>
          </div>
          <div className="p-3 bg-white/70 rounded-lg">
            <Sparkles className="w-5 h-5 mx-auto mb-1 text-indigo-600" />
            <p className="text-xs font-medium">2. Extract</p>
            <p className="text-xs text-gray-500">AI pulls ICD-10, treatments, implant</p>
          </div>
          <div className="p-3 bg-white/70 rounded-lg">
            <FileDown className="w-5 h-5 mx-auto mb-1 text-green-600" />
            <p className="text-xs font-medium">3. Submit</p>
            <p className="text-xs text-gray-500">Download PDF or copy narrative</p>
          </div>
        </div>

        <button
          onClick={onTryDemo}
          disabled={isDemoLoading}
          className="mt-2 px-6 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg font-semibold text-sm hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50"
        >
          {isDemoLoading ? "Processing sample note..." : "Try it now with a sample case"}
        </button>
      </div>
    </div>
  );
}
