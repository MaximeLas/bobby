import FeatureCard from './FeatureCard';
import './Features.css';

export default function Features() {
  const features = [
    {
      icon: '📋',
      title: 'Smart Task Management',
      description: 'Create, assign, and track tasks with powerful filtering and search. Never lose track of what needs to be done.'
    },
    {
      icon: '👥',
      title: 'Team Collaboration',
      description: 'Work together seamlessly with real-time updates, comments, and file sharing. Keep everyone on the same page.'
    },
    {
      icon: '📊',
      title: 'Visual Progress Tracking',
      description: 'Beautiful dashboards and reports help you understand your team\'s progress at a glance. Make data-driven decisions.'
    },
    {
      icon: '🔔',
      title: 'Smart Notifications',
      description: 'Stay informed with customizable notifications. Get alerts for what matters most to you and your team.'
    }
  ];

  return (
    <section className="features">
      <div className="features-container">
        <h2 className="features-heading">Everything you need to succeed</h2>
        <p className="features-subheading">
          Powerful features designed to help your team work better together
        </p>
        <div className="features-grid">
          {features.map((feature, index) => (
            <FeatureCard key={index} {...feature} />
          ))}
        </div>
      </div>
    </section>
  );
}
