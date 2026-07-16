$ErrorActionPreference = "Stop"

$frontend = 'C:\Users\kumar\desktop\Sakhi-AI-frontend'

$siteNav = @'
import Link from "next/link";

type NavItem = {
  href: string;
  label: string;
};

type SiteNavProps = {
  items: NavItem[];
};

export function SiteNav({ items }: SiteNavProps) {
  return (
    <header className="flex flex-col gap-4 rounded-[1.5rem] border border-peach/60 bg-white/80 px-5 py-4 shadow-sm backdrop-blur lg:flex-row lg:items-center lg:justify-between">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-moss">Sakhi AI</p>
          <p className="mt-1 text-sm text-berry/80">Trusted health education, made calmer.</p>
        </div>

        <div className="flex items-center gap-2 lg:hidden">
          <Link
            href="/login"
            className="rounded-full border border-berry/20 bg-white px-4 py-2 text-sm font-medium text-berry transition hover:border-berry/30 hover:bg-peach/35"
          >
            Login
          </Link>
          <Link
            href="/register"
            className="inline-flex items-center justify-center rounded-full bg-gradient-to-r from-rose to-berry px-4 py-2 text-sm font-semibold text-white transition hover:from-berry hover:to-rose"
          >
            Sign up
          </Link>
        </div>
      </div>

      <nav aria-label="Primary" className="flex flex-wrap gap-2">
        {items.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="rounded-full border border-berry/10 bg-white px-4 py-2 text-sm font-medium text-ink transition hover:border-berry/20 hover:bg-peach/50"
          >
            {item.label}
          </Link>
        ))}
      </nav>

      <div className="hidden items-center gap-2 lg:flex">
        <Link
          href="/login"
          className="rounded-full border border-berry/20 bg-white px-4 py-2 text-sm font-medium text-berry transition hover:border-berry/30 hover:bg-peach/35"
        >
          Login
        </Link>
        <Link
          href="/register"
          className="inline-flex items-center justify-center rounded-full bg-gradient-to-r from-rose to-berry px-4 py-2 text-sm font-semibold text-white transition hover:from-berry hover:to-rose"
        >
          Sign up
        </Link>
      </div>
    </header>
  );
}
'@
Set-Content -LiteralPath (Join-Path $frontend 'components\home\SiteNav.tsx') -Value $siteNav -Encoding utf8

$homePage = Get-Content -LiteralPath (Join-Path $frontend 'app\page.tsx') -Raw
$homePage = $homePage.Replace('        <SiteNav items={navItems} ctaLabel="Explore chat" ctaHref="#chat" />', '        <SiteNav items={navItems} />')
Set-Content -LiteralPath (Join-Path $frontend 'app\page.tsx') -Value $homePage -Encoding utf8

$implPath = Join-Path $frontend 'IMPLEMENTATION.md'
$impl = Get-Content -LiteralPath $implPath -Raw
$impl = $impl.Replace('| `components/home/SiteNav.tsx` | `components/home/SiteNav.tsx` | Public landing page navigation |', '| `components/home/SiteNav.tsx` | Public landing page navigation - section links plus Login/Sign up actions in the navbar |')
$impl = $impl.Replace('- The search page is now complete with filters, curated results, and quick links.`r`n- The chat page now renders the stored message content instead of a hardcoded placeholder.`r`n- The next frontend pages are FAQ and Help.', '- The search page is now complete with filters, curated results, and quick links.`r`n- The chat page now renders the stored message content instead of a hardcoded placeholder.`r`n- The landing page navbar now includes explicit Login and Sign up actions.`r`n- The next frontend pages are FAQ and Help.')
if ($impl -notmatch 'landing page navbar now includes explicit Login and Sign up actions') {
  $impl = $impl -replace '(- The chat page now renders the stored message content instead of a hardcoded placeholder\.)', '$1`r`n- The landing page navbar now includes explicit Login and Sign up actions.'
}
Set-Content -LiteralPath $implPath -Value $impl -Encoding utf8

