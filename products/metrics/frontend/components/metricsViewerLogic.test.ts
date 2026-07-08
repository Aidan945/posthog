import { router } from 'kea-router'

import api from 'lib/api'

import { initKeaTests } from '~/test/init'

import { metricNamePickerLogic } from './metricNamePickerLogic'
import { metricsViewerLogic } from './metricsViewerLogic'

const PICKER_ITEMS = [
    { name: 'requests_total', metric_type: 'sum' },
    { name: 'queue_depth', metric_type: 'gauge' },
    { name: 'request_duration', metric_type: 'histogram' },
    { name: 'mystery_metric', metric_type: 'unknown_type' },
]

describe('metricsViewerLogic', () => {
    let logic: ReturnType<typeof metricsViewerLogic.build>

    beforeEach(() => {
        initKeaTests()
        jest.spyOn(api.metrics, 'values').mockResolvedValue({ results: PICKER_ITEMS })
        logic = metricsViewerLogic()
        logic.mount()
        metricNamePickerLogic.actions.loadItemsSuccess(PICKER_ITEMS)
    })

    afterEach(() => {
        logic?.unmount()
    })

    // Regression: the viewer defaulted every metric to `sum`, so selecting a
    // cumulative counter summed raw monotonic readings across pods and buckets —
    // a huge meaningless total instead of the actual increase.
    it.each([
        ['requests_total', 'increase'],
        ['queue_depth', 'avg'],
        ['request_duration', 'p95'],
    ])('selecting %s applies the type-appropriate aggregation %s', (metricName, expected) => {
        logic.actions.setMetricName(metricName)
        expect(logic.values.aggregation).toBe(expected)
    })

    it('keeps a manual aggregation pick until the metric changes', () => {
        logic.actions.setMetricName('requests_total')
        logic.actions.setAggregation('rate')
        expect(logic.values.aggregation).toBe('rate')
        logic.actions.setMetricName('queue_depth')
        expect(logic.values.aggregation).toBe('avg')
    })

    it('leaves aggregation untouched for unknown metric types', () => {
        logic.actions.setMetricName('requests_total')
        logic.actions.setMetricName('mystery_metric')
        expect(logic.values.aggregation).toBe('increase')
    })

    it('applies viewer state from URL params', () => {
        router.actions.push('/metrics', {
            metricName: 'queue_depth',
            aggregation: 'rate',
            dateFrom: '-24h',
            filters: ['env=prod'],
            groupBy: ['service.name'],
            viewMode: 'stat',
            statSummary: 'total',
        })
        expect(logic.values.metricName).toBe('queue_depth')
        expect(logic.values.aggregation).toBe('rate')
        expect(logic.values.dateFrom).toBe('-24h')
        expect(logic.values.filterStrings).toEqual(['env=prod'])
        expect(logic.values.groupByKeys).toEqual(['service.name'])
        expect(logic.values.viewMode).toBe('stat')
        expect(logic.values.statSummary).toBe('total')
    })

    it('ignores invalid enum params from the URL', () => {
        router.actions.push('/metrics', { aggregation: 'nonsense', viewMode: 'nonsense' })
        expect(logic.values.aggregation).toBe('sum')
        expect(logic.values.viewMode).toBe('chart')
    })

    it('writes state to the URL and omits defaults', () => {
        router.actions.push('/metrics')
        logic.actions.setMetricName('queue_depth')
        expect(router.values.searchParams.metricName).toBe('queue_depth')
        expect(router.values.searchParams.aggregation).toBe('avg')
        expect('viewMode' in router.values.searchParams).toBe(false)
        expect('dateFrom' in router.values.searchParams).toBe(false)
    })

    it('applies a saved state, letting an explicit aggregation win over the recommended one', () => {
        logic.actions.applySavedState({
            metricName: 'queue_depth',
            aggregation: 'p95',
            filters: ['env=prod'],
            viewMode: 'stat',
        })
        expect(logic.values.metricName).toBe('queue_depth')
        expect(logic.values.aggregation).toBe('p95')
        expect(logic.values.filterStrings).toEqual(['env=prod'])
        expect(logic.values.viewMode).toBe('stat')
    })
})
