/**
 * Компонент: модальное окно для создания/редактирования лимита.
 */
const LimitModal = {
    template: `
        <a-modal v-model:visible="visible" :title="isNew ? 'Новый лимит' : 'Редактировать лимит'"
            @ok="handleSave" :okText="isNew ? 'Создать' : 'Сохранить'" :confirmLoading="saving">
            <a-form layout="vertical">
                <a-form-item label="Приложение">
                    <a-select v-model:value="form.system_id" :disabled="!isNew"
                        :options="appOptions" placeholder="Выберите приложение" />
                </a-form-item>
                <a-form-item label="Лимит (минут)">
                    <a-input-number v-model:value="form.limit_minutes" :min="1" :max="1440" style="width:100%" />
                </a-form-item>
                <a-form-item>
                    <a-switch v-model:checked="form.enabled"
                        checked-children="Активен" un-checked-children="Отключён" />
                </a-form-item>
            </a-form>
        </a-modal>
    `,
    props: {
        visible: Boolean,
        isNew: Boolean,
        form: Object,
        appOptions: Array,
        saving: Boolean,
    },
    emits: ['update:visible', 'save'],
    setup(props, { emit }) {
        function handleSave() {
            emit('save', { ...props.form });
        }
        return { handleSave };
    },
};
