import { useState } from 'react';
import PricingCard from './PricingCard';
import './Pricing.css';

export default function Pricing() {
  const [isAnnual, setIsAnnual] = useState(false);

  const pricingTiers = [
    {
      tier: 'Basic',
      monthlyPrice: 10,
      annualPrice: 96,
      description: 'Perfect for small teams and freelancers',
      features: [
        'Up to 5 team members',
        'Up to 10 projects',
        'Basic task management',
        'Basic notifications',
        'Basic support'
      ],
      buttonText: 'Start 14-Day Trial'
    },
    {
      tier: 'Pro',
      monthlyPrice: 25,
      annualPrice: 240,
      description: 'Ideal for growing teams',
      features: [
        'Up to 25 team members',
        'Unlimited projects',
        'Smart Notifications',
        'Visual Progress Tracking',
        'Advanced analytics & reporting',
        'Priority support'
      ],
      buttonText: 'Start 14-Day Trial',
      isPopular: true
    },
    {
      tier: 'Enterprise',
      monthlyPrice: null,
      annualPrice: null,
      description: 'For large organizations',
      features: [
        'Unlimited team members',
        'Unlimited projects',
        'Dedicated account manager',
        'Custom integrations',
        'SSO authentication',
        'Advanced security & permissions',
        'Audit logs',
        '24/7 premium support'
      ],
      buttonText: 'Contact Sales'
    }
  ];

  return (
    <section className="pricing">
      <div className="pricing-container">
        <h2 className="pricing-heading">Simple, Transparent Pricing</h2>
        <p className="pricing-subheading">No hidden fees. Cancel anytime.</p>

        <div className="pricing-toggle">
          <span className={`pricing-toggle-label ${!isAnnual ? 'active' : ''}`}>
            Monthly
          </span>
          <button
            className="pricing-toggle-switch"
            onClick={() => setIsAnnual(!isAnnual)}
            aria-label="Toggle between monthly and annual pricing"
          >
            <div className={`pricing-toggle-slider ${isAnnual ? 'annual' : ''}`} />
          </button>
          <span className={`pricing-toggle-label ${isAnnual ? 'active' : ''}`}>
            Annual
            <span className="pricing-toggle-discount">Save 20%</span>
          </span>
        </div>

        <div className="pricing-grid">
          {pricingTiers.map((tier, index) => (
            <PricingCard
              key={index}
              tier={tier.tier}
              price={isAnnual ? tier.annualPrice : tier.monthlyPrice}
              period={isAnnual ? 'year' : 'month'}
              description={tier.description}
              features={tier.features}
              buttonText={tier.buttonText}
              isPopular={tier.isPopular}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
