"use client";

import { ExternalLink } from "lucide-react";
import { Legislation, Supervisor } from "@/types/legislation";

type Props = {
  legislation: Legislation;
  supervisors: Supervisor[];
};

export default function LegislationCard({ legislation, supervisors }: Props) {
  // Helper functions
  const getVoteColor = (vote?: string) => {
    if (vote === "yes") return "bg-green-100 text-green-800 border-green-300";
    if (vote === "no") return "bg-red-100 text-red-800 border-red-300";
    return "bg-gray-100 text-gray-800 border-gray-300";
  };

  const getStatusColor = (status?: string) => {
    if (status === "Passed") return "bg-green-100 text-green-800 border-green-300";
    if (status === "Failed") return "bg-red-100 text-red-800 border-red-300";
    if (status === "Pending Committee Action")
      return "bg-yellow-100 text-yellow-800 border-yellow-300";
    if (status === "Pending") return "bg-blue-100 text-blue-800 border-blue-300";
    return "bg-gray-100 text-gray-800 border-gray-300";
  };

  const yesVotes = Object.entries(legislation.votes || {}).filter(
    ([, v]) => v === "yes"
  );
  const noVotes = Object.entries(legislation.votes || {}).filter(
    ([, v]) => v === "no"
  );

  const yesCount = yesVotes.length;
  const noCount = noVotes.length;

  return (
    <div className="border border-gray-200 rounded-lg bg-white p-6 hover:shadow-sm transition-shadow">
      <div className="flex flex-col gap-2 mb-2">
        <div className="flex items-center flex-wrap gap-2 text-sm text-gray-700">
          <span className="text-blue-700 font-semibold">
            {legislation.legislation_number}
          </span>
          <span className="px-2 py-1 bg-gray-100 rounded text-xs font-medium">
            {legislation.type}
          </span>
          <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-medium">
            {legislation.category}
          </span>
          <span
            className={`px-2 py-1 rounded border text-xs font-medium ${getStatusColor(
              legislation.status
            )}`}
          >
            {legislation.status}
          </span>
          <span className="text-sm text-gray-500">
            {new Date(legislation.dates?.final_action || "").toLocaleDateString()}
          </span>
        </div>

        <h3 className="text-lg font-semibold text-gray-900">
          {legislation.title}
        </h3>
      </div>

      <p className="text-sm text-gray-700 mb-3">
        {legislation.description || "No description available."}
      </p>

      <div className="flex items-center gap-3 flex-wrap text-sm text-gray-600 mb-3">
        {legislation.sponsors?.length > 0 && (
          <span>
            <span className="font-medium">Sponsors:</span>{" "}
            {legislation.sponsors.map((s) => s.name).join(", ")}
          </span>
        )}
        {legislation.committee?.name && (
          <span>
            <span className="font-medium">Committee:</span>{" "}
            {legislation.committee.name}
          </span>
        )}
      </div>

      <div className="flex items-center gap-6 text-sm mb-3">
        <span className="font-medium text-gray-800">
          Result: {legislation.status}
        </span>
        <span className="text-green-700 font-medium">
          Yes: {yesCount}
        </span>
        <span className="text-red-700 font-medium">
          No: {noCount}
        </span>
      </div>

      <div className="flex gap-1 mb-3">
        {yesVotes.slice(0, 5).map(([name]) => {
          const sup = supervisors.find((s) => s.name === name);
          const initials =
            sup?.initials || name.split(" ").map((n) => n[0]).join("");
          return (
            <div
              key={name}
              className="w-8 h-8 rounded-full bg-green-700 text-white flex items-center justify-center text-xs font-bold border-2 border-white"
              title={`${name} (Yes)`}
            >
              {initials}
            </div>
          );
        })}
        {yesCount > 5 && (
          <div className="w-8 h-8 rounded-full bg-green-600 text-white flex items-center justify-center text-xs font-bold border-2 border-white">
            +{yesCount - 5}
          </div>
        )}
        {noVotes.slice(0, 3).map(([name]) => {
          const sup = supervisors.find((s) => s.name === name);
          const initials =
            sup?.initials || name.split(" ").map((n) => n[0]).join("");
          return (
            <div
              key={name}
              className="w-8 h-8 rounded-full bg-red-700 text-white flex items-center justify-center text-xs font-bold border-2 border-white"
              title={`${name} (No)`}
            >
              {initials}
            </div>
          );
        })}
      </div>

      <a
        href={legislation.legislation_url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800"
      >
        View Full Legislation <ExternalLink className="h-3 w-3" />
      </a>
    </div>
  );
}
