"use client";

import { useState } from "react";
import type { ReactNode } from "react";

type Company = {
  company_name?: string | null;
  legal_name?: string | null;
  industry?: string | null;
  company_category?: string | null;
  description?: string | null;
  founded_year?: string | number | null;
  employee_count?: string | null;
  employee_range?: string | null;
  company_type?: string | null;

  headquarters?: string | null;
  locations?: string[];

  emails?: string[];
  phone_numbers?: string[];

  social_media?: {
    linkedin?: string[];
    instagram?: string[];
    facebook?: string[];
    twitter?: string[];
    youtube?: string[];
    tiktok?: string[];
    github?: string[];
    pinterest?: string[];
  };

  services?: string[];
  products?: string[];
  industries_served?: string[];

  founders?: string[];
  ceo?: string | null;
  leadership?: string[];

  contact_page?: string | null;
  about_page?: string | null;
  careers_page?: string | null;

  certifications?: string[];
  awards?: string[];
  clients?: string[];
  partners?: string[];

  technologies?: string[];
  markets?: string[];

  additional_information?: string[];
};

type Result = {
  success: boolean;
  website: string;
  pages_analyzed: number;
  company: Company;
  sources: {
    url: string;
    title: string;
  }[];
};

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [url, setUrl] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function analyzeWebsite() {
    setError("");
    setResult(null);

    if (!url.trim()) {
      setError("Please enter a company website.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Analysis failed.");
      }

      setResult(data);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Something went wrong.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto max-w-6xl px-6 py-16">
        <div className="mb-12 text-center">
          <div className="mb-4 inline-block rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-300">
            Company Intelligence
          </div>

          <h1 className="text-5xl font-bold tracking-tight">
            Analyze Any Company
          </h1>

          <p className="mx-auto mt-5 max-w-2xl text-lg text-slate-400">
            Enter a company&apos;s website and automatically extract
            publicly available company information.
          </p>
        </div>

        <div className="mx-auto max-w-3xl">
          <div className="flex gap-3 rounded-2xl border border-slate-800 bg-slate-900 p-3">
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  analyzeWebsite();
                }
              }}
              placeholder="https://company.com"
              className="flex-1 rounded-xl bg-slate-950 px-5 py-4 outline-none placeholder:text-slate-600"
            />

            <button
              onClick={analyzeWebsite}
              disabled={loading}
              className="rounded-xl bg-white px-7 py-4 font-semibold text-black transition hover:bg-slate-200 disabled:opacity-50"
            >
              {loading ? "Analyzing..." : "Analyze"}
            </button>
          </div>

          {error && (
            <div className="mt-4 rounded-xl border border-red-900 bg-red-950/40 p-4 text-red-300">
              {error}
            </div>
          )}
        </div>

        {loading && (
          <div className="mx-auto mt-12 max-w-3xl rounded-2xl border border-slate-800 bg-slate-900 p-8">
            <div className="mb-4 text-lg font-semibold">
              Analyzing company...
            </div>

            <div className="h-2 overflow-hidden rounded-full bg-slate-800">
              <div className="h-full w-2/3 animate-pulse bg-white" />
            </div>

            <div className="mt-5 space-y-2 text-sm text-slate-400">
              <p>✓ Connecting to website</p>
              <p>✓ Discovering company pages</p>
              <p>✓ Extracting contact information</p>
              <p>✓ Finding social profiles</p>
              <p>✓ Analyzing company information</p>
            </div>
          </div>
        )}

        {result && (
          <CompanyDashboard
            company={result.company}
            website={result.website}
            pagesAnalyzed={result.pages_analyzed}
            sources={result.sources}
          />
        )}
      </div>
    </main>
  );
}

function CompanyDashboard({
  company,
  website,
  pagesAnalyzed,
  sources,
}: {
  company: Company;
  website: string;
  pagesAnalyzed: number;
  sources: {
    url: string;
    title: string;
  }[];
}) {
  return (
    <div className="mt-12 space-y-6">
      <section className="rounded-3xl border border-slate-800 bg-slate-900 p-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-sm text-slate-500">COMPANY</p>

            <h2 className="mt-2 text-4xl font-bold">
              {company.company_name || "Company name not found"}
            </h2>

            <p className="mt-3 text-slate-400">
              {company.description || "No description found."}
            </p>
          </div>

          <div className="rounded-xl bg-slate-950 px-4 py-3 text-sm text-slate-400">
            {pagesAnalyzed} pages analyzed
          </div>
        </div>

        <div className="mt-8 grid gap-4 md:grid-cols-4">
          <Info
            label="Industry"
            value={company.industry || company.company_category}
          />

          <Info label="Founded" value={company.founded_year} />

          <Info
            label="Employees"
            value={company.employee_count || company.employee_range}
          />

          <Info label="Company Type" value={company.company_type} />
        </div>
      </section>

      <div className="grid gap-6 md:grid-cols-2">
        <Card title="Contact Information">
          <List label="Emails" items={company.emails} />
          <List label="Phone Numbers" items={company.phone_numbers} />
          <Info label="Headquarters" value={company.headquarters} />
        </Card>

        <Card title="Social Media">
          <Social name="LinkedIn" links={company.social_media?.linkedin} />
          <Social name="Instagram" links={company.social_media?.instagram} />
          <Social name="Facebook" links={company.social_media?.facebook} />
          <Social name="X / Twitter" links={company.social_media?.twitter} />
          <Social name="YouTube" links={company.social_media?.youtube} />
          <Social name="TikTok" links={company.social_media?.tiktok} />
        </Card>

        <Card title="Business">
          <List label="Services" items={company.services} />
          <List label="Products" items={company.products} />
          <List
            label="Industries Served"
            items={company.industries_served}
          />
        </Card>

        <Card title="People">
          <List label="Founders" items={company.founders} />
          <Info label="CEO" value={company.ceo} />
          <List label="Leadership" items={company.leadership} />
        </Card>

        <Card title="Locations">
          <List label="Locations" items={company.locations} />
          <List label="Markets" items={company.markets} />
        </Card>

        <Card title="Company Intelligence">
          <List label="Technologies" items={company.technologies} />
          <List label="Certifications" items={company.certifications} />
          <List label="Awards" items={company.awards} />
          <List label="Clients" items={company.clients} />
          <List label="Partners" items={company.partners} />
        </Card>
      </div>

      <Card title="Important Pages">
        <LinkItem label="Website" url={website} />
        <LinkItem label="About" url={company.about_page} />
        <LinkItem label="Contact" url={company.contact_page} />
        <LinkItem label="Careers" url={company.careers_page} />
      </Card>

      <Card title="Sources">
        <p className="mb-4 text-sm text-slate-400">
          These are the pages that were analyzed.
        </p>

        <div className="space-y-2">
          {sources.map((source) => (
            <a
              key={source.url}
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block rounded-xl bg-slate-950 p-4 transition hover:bg-slate-800"
            >
              <div className="font-medium">
                {source.title || "Untitled page"}
              </div>

              <div className="mt-1 break-all text-sm text-slate-500">
                {source.url}
              </div>
            </a>
          ))}
        </div>
      </Card>
    </div>
  );
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900 p-7">
      <h3 className="mb-6 text-xl font-semibold">{title}</h3>

      <div className="space-y-5">{children}</div>
    </section>
  );
}

function Info({
  label,
  value,
}: {
  label: string;
  value?: string | number | null;
}) {
  return (
    <div className="rounded-2xl bg-slate-950 p-5">
      <div className="text-xs uppercase tracking-wider text-slate-500">
        {label}
      </div>

      <div className="mt-2 break-words font-medium">
        {value || "Not found"}
      </div>
    </div>
  );
}

function List({ label, items }: { label: string; items?: string[] }) {
  if (!items || items.length === 0) {
    return (
      <div>
        <div className="text-sm text-slate-500">{label}</div>

        <div className="mt-1 text-slate-600">Not found</div>
      </div>
    );
  }

  return (
    <div>
      <div className="text-sm text-slate-500">{label}</div>

      <ul className="mt-2 space-y-2">
        {items.map((item, index) => (
          <li key={`${item}-${index}`} className="rounded-xl bg-slate-950 p-3">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

function Social({ name, links }: { name: string; links?: string[] }) {
  if (!links || links.length === 0) {
    return (
      <div className="flex justify-between border-b border-slate-800 pb-3">
        <span className="text-slate-400">{name}</span>
        <span className="text-slate-600">Not found</span>
      </div>
    );
  }

  return (
    <div className="border-b border-slate-800 pb-3">
      <div className="mb-2 text-slate-400">{name}</div>

      {links.map((link) => (
        <a
          key={link}
          href={link}
          target="_blank"
          rel="noopener noreferrer"
          className="block break-all text-sm text-blue-400 hover:underline"
        >
          {link}
        </a>
      ))}
    </div>
  );
}

function LinkItem({ label, url }: { label: string; url?: string | null }) {
  return (
    <div className="flex flex-col gap-2 border-b border-slate-800 pb-4 md:flex-row md:items-center md:justify-between">
      <span className="text-slate-400">{label}</span>

      {url ? (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="break-all text-blue-400 hover:underline"
        >
          {url}
        </a>
      ) : (
        <span className="text-slate-600">Not found</span>
      )}
    </div>
  );
}
