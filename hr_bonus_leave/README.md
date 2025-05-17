# HR Bonus Leave

This module automatically allocates annual bonus leave to employees based on their years of service in the organization.

## Features

- Automatically calculates years of service for each employee based on their date of joining
- Adds a new leave type for bonus leave allocations
- Configurable policy for minimum years of service and maximum bonus days
- Annual automated allocation via scheduled cron job
- Manual allocation option for HR managers
- Maintains allocation logs to prevent duplicate allocations
- Easy to view allocation history

## Bonus Leave Policy

The module implements the following default policy:

- Employees with 3+ years of service qualify for bonus leave
- Bonus leave days are calculated as: (Years of Service - Minimum Years + 1)
  - 3 years → 1 day
  - 4 years → 2 days
  - 5 years → 3 days
  - And so on
- Maximum bonus leave days can be configured (default is 10 days)

## Configuration

The bonus leave policy can be configured in the Time Off settings:

1. Go to **Time Off > Configuration > Settings**
2. Find the **Bonus Leave Policy** section
3. Configure:
   - Minimum years of service (default: 3)
   - Maximum bonus days (default: 10)

## Usage

### Automatic Allocation

By default, a scheduled job runs on January 1st each year to allocate bonus leave to all eligible employees. This ensures each employee receives their bonus leave only once per year.

### Manual Allocation

HR Managers can manually allocate bonus leave:

1. Go to **Time Off > Bonus Leave > Allocate Bonus Leave**
2. Select the employees and the allocation year
3. Click **Allocate**

### Viewing Allocation History

To view the history of bonus leave allocations:

1. Go to **Time Off > Bonus Leave > Allocation History**
2. Filter or group by employee, allocation year, etc.

## Technical Information

- The module extends the standard hr.employee model to add years of service calculation
- A new model tracks allocation history to prevent duplicates
- Bonus leave is granted based on the configured policy

## Future Enhancements

- Email notifications to employees when bonus leave is allocated
- More granular configuration options for the bonus leave policy 