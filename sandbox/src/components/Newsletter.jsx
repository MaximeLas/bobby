import { useState } from 'react';
import Button from './Button';
import './Newsletter.css';

export default function Newsletter() {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState('idle'); // idle, loading, success, error

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!email) return;

    setStatus('loading');

    // Simulate API call - replace with actual newsletter signup logic
    setTimeout(() => {
      setStatus('success');
      setEmail('');

      // Reset success message after 3 seconds
      setTimeout(() => {
        setStatus('idle');
      }, 3000);
    }, 500);
  };

  return (
    <section className="newsletter">
      <div className="newsletter-container">
        <h2 className="newsletter-heading">Stay in the loop</h2>
        <p className="newsletter-subheading">
          Get product updates, tips, and announcements delivered to your inbox.
        </p>

        <form className="newsletter-form" onSubmit={handleSubmit}>
          <input
            type="email"
            className="newsletter-input"
            placeholder="Enter your email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={status === 'loading' || status === 'success'}
          />
          <Button
            variant="primary"
            onClick={handleSubmit}
          >
            {status === 'loading' ? 'Subscribing...' : status === 'success' ? 'Subscribed!' : 'Subscribe'}
          </Button>
        </form>

        {status === 'success' && (
          <p className="newsletter-success">
            Thanks for subscribing! Check your inbox to confirm.
          </p>
        )}
      </div>
    </section>
  );
}
