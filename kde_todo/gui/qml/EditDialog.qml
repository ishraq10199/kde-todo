import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Kirigami.Dialog {
    id: dialog

    property var item: ({})
    property var tags: []

    function openFor(data) {
        item = data
        titleField.text = data.title
        durationField.text = `${data.duration}m`
        atField.text = data.fixedStart
        notesField.text = data.notes
        tags = data.tagsText ? data.tagsText.split(" ").map(t => t.replace(/^#/, "")) : []
        tagField.clear()
        open()
    }

    // "code review" or "#code, #review" adds both; tags already there are skipped.
    function addTags(text) {
        const next = tags.slice()
        for (const word of text.replace(/,/g, " ").split(/\s+/)) {
            const tag = word.replace(/^#+/, "")
            if (tag && !next.some(t => t.toLowerCase() === tag.toLowerCase()))
                next.push(tag)
        }
        tags = next
        tagField.clear()
    }

    title: item.isBreak ? "Edit break" : "Edit item"
    padding: Kirigami.Units.largeSpacing
    preferredWidth: Kirigami.Units.gridUnit * 22
    standardButtons: Kirigami.Dialog.Cancel

    customFooterActions: Kirigami.Action {
        icon.name: "document-save"
        text: "Save"
        onTriggered: {
            if (tagField.text.trim())
                dialog.addTags(tagField.text)
            backend.edit(dialog.item.id, titleField.text, durationField.text, atField.text, notesField.text,
                         dialog.tags.join(" "))
            dialog.close()
        }
    }

    Kirigami.FormLayout {
        QQC2.TextField {
            id: titleField
            visible: !dialog.item.isBreak
            Kirigami.FormData.label: "Title:"
        }
        QQC2.TextField {
            id: durationField
            Kirigami.FormData.label: "Duration:"
            placeholderText: "45m, 1h30m"
        }
        QQC2.TextField {
            id: atField
            Kirigami.FormData.label: "Fixed start:"
            placeholderText: "HH:MM, or leave empty"
        }
        Flow {
            Kirigami.FormData.label: "Tags:"
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing
            visible: dialog.tags.length > 0
            Repeater {
                model: dialog.tags
                Pill {
                    required property string modelData
                    required property int index
                    tag: modelData
                    removable: true
                    onRemoveClicked: dialog.tags = dialog.tags.filter((_, i) => i !== index)
                }
            }
        }
        Kirigami.ActionTextField {
            id: tagField
            Kirigami.FormData.label: dialog.tags.length > 0 ? "" : "Tags:"
            placeholderText: "Add a tag, then Enter"
            onAccepted: dialog.addTags(text)
            rightActions: Kirigami.Action {
                icon.name: "list-add"
                text: "Add tag"
                enabled: tagField.text.trim().length > 0
                onTriggered: dialog.addTags(tagField.text)
            }
        }
        QQC2.TextArea {
            id: notesField
            Kirigami.FormData.label: "Notes:"
            Layout.fillWidth: true
            Layout.minimumHeight: Kirigami.Units.gridUnit * 4
            wrapMode: TextEdit.Wrap
        }
    }
}
