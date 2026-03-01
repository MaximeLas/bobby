import './LogoSection.css';

export default function LogoSection() {
  const companies = [
    { name: 'Acme Corp', logo: 'ACME' },
    { name: 'TechStart', logo: 'TECHSTART' },
    { name: 'Innovate Co', logo: 'INNOVATE' },
    { name: 'Digital Labs', logo: 'DIGITAL' },
    { name: 'Future Inc', logo: 'FUTURE' },
    { name: 'Growth Partners', logo: 'GROWTH' },
    { name: 'Apex Systems', logo: 'APEX' },
    { name: 'Venture Group', logo: 'VENTURE' }
  ];

  return (
    <section className="logo-section">
      <div className="logo-section-container">
        <h3 className="logo-section-heading">Trusted by leading teams</h3>
        <div className="logo-section-grid">
          {companies.map((company) => (
            <div key={company.name} className="logo-item">
              <div className="logo-placeholder">{company.logo}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
