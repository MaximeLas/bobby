import Button from './Button';
import './PricingCard.css';

export default function PricingCard({
  tier,
  price,
  period,
  description,
  features,
  buttonText,
  isPopular
}) {
  return (
    <div className={`pricing-card ${isPopular ? 'pricing-card-popular' : ''}`}>
      {isPopular && <div className="pricing-badge">Most Popular</div>}
      <h3 className="pricing-tier">{tier}</h3>
      {price ? (
        <div className="pricing-price">
          <span className="pricing-dollar">$</span>
          <span className="pricing-amount">{price}</span>
          <span className="pricing-period">/{period}</span>
        </div>
      ) : (
        <div className="pricing-price">
          <span className="pricing-contact">Contact Sales</span>
        </div>
      )}
      <p className="pricing-description">{description}</p>
      <ul className="pricing-features">
        {features.map((feature, index) => (
          <li key={index} className="pricing-feature">
            <span className="pricing-checkmark">✓</span>
            {feature}
          </li>
        ))}
      </ul>
      <Button variant={isPopular ? 'primary' : 'secondary'}>
        {buttonText}
      </Button>
    </div>
  );
}
